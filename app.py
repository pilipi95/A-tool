import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta
import io
import datetime
from concurrent.futures import ThreadPoolExecutor
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# SEITEN-KONFIGURATION
# ==========================================
st.set_page_config(
    page_title="GEILEPROFITE | Aktienanalyse",
    page_icon="🤑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CUSTOM CSS (CLEAN & INTUITIVE UI)
# ==========================================
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #21262d;
    }

    /* Einheitliche KPI-Karten */
    div[data-testid="stMetric"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 12px 16px;
        min-height: 98px !important;
        height: 98px !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: border-color 0.15s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #58a6ff;
    }

    /* Urteils-Karte im Header */
    .verdict-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 12px 16px;
        min-height: 98px !important;
        height: 98px !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .verdict-label {
        font-size: 13px;
        color: #8b949e;
        margin-bottom: 4px;
    }
    .verdict-value {
        font-size: 18px;
        font-weight: 700;
        margin: 0;
    }
    .verdict-sub {
        font-size: 12px;
        color: #8b949e;
        margin-top: 2px;
    }
    .verdict-buy { border-left: 4px solid #2ea043; }
    .verdict-hold { border-left: 4px solid #d29922; }
    .verdict-sell { border-left: 4px solid #f85149; }

    /* Saubere Haupt-Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #21262d;
        margin-bottom: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-bottom: none;
        border-radius: 8px 8px 0 0;
        color: #8b949e;
        padding: 10px 18px;
        font-size: 14px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #21262d !important;
        color: #ffffff !important;
        border-color: #58a6ff !important;
        font-weight: 600;
    }

    /* Buttons */
    .stButton > button, .stDownloadButton > button {
        background-color: #21262d;
        color: #e6edf3;
        border: 1px solid #30363d;
        border-radius: 8px;
        font-weight: 500;
        font-size: 13px;
        transition: all 0.15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background-color: #30363d;
        border-color: #58a6ff;
        color: #ffffff;
    }

    h1, h2, h3 {
        color: #f0f6fc !important;
        font-weight: 600 !important;
        letter-spacing: -0.3px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# KONSTANTEN & PRESETS
# ==========================================
SCREENER_LISTS = {
    "US Big Tech & Growth": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "NFLX", "INTC",
        "CRM", "ORCL", "PLTR", "AVGO", "AMAT", "NOW", "UBER", "ABNB", "PANW", "SNOW"
    ],
    "Nasdaq 100 Focus": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "ASML",
        "AZN", "AMD", "PEP", "LIN", "NFLX", "ADBE", "TMUS", "CSCO", "PDD", "INTC",
        "QCOM", "TXN", "CMCSA", "AMGN", "INTU", "HON", "AMAT", "BKNG", "ISRG", "ADP"
    ],
    "S&P 500 Top Pick Mix": [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "JNJ", "JPM", "V",
        "PG", "UNH", "HD", "MA", "DIS", "ABBV", "BAC", "CVX", "LLY", "MRK",
        "PFE", "KO", "PEP", "TMO", "WMT", "MCD", "CSCO", "XOM", "COST", "CAT"
    ],
    "DAX 40 (Deutschland)": [
        "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "MBG.DE", "BMW.DE", "VOW3.DE", "BAS.DE",
        "RHM.DE", "BAYN.DE", "AIR.DE", "DTG.DE", "MUV2.DE", "IFX.DE", "DHL.DE", "DB1.DE",
        "SY1.DE", "BEI.DE", "CON.DE", "EON.DE", "HEI.DE", "HEN3.DE", "MRK.DE", "QIAG.DE"
    ],
    "MDAX & Mid-Caps (DE)": [
        "P911.DE", "LHA.DE", "EVT.DE", "HFG.DE", "TKAG.DE", "FPE3.DE", "BOSS.DE", "G1A.DE",
        "AIXA.DE", "NEM.DE", "SRT3.DE", "HAG.DE", "ENR.DE", "DEQ.DE"
    ],
    "Euro Stoxx 50 (Europa)": [
        "ASML.AS", "MC.PA", "SAP.DE", "OR.PA", "TTE.PA", "SIE.DE", "ALV.DE", "SU.PA",
        "SAN.MC", "SAN.PA", "CDI.PA", "IBE.MC", "BNP.PA", "AIR.PA", "ENEL.MI", "BBVA.MC"
    ],
    "Dividenden-Aristokraten": [
        "JNJ", "PG", "KO", "PEP", "MMM", "ABBV", "CVX", "XOM", "TGT", "LOW",
        "EMR", "ITW", "O", "ADP", "GD", "MCD", "WMT", "CL"
    ],
    "Cybersecurity & AI Tech": [
        "NVDA", "PLTR", "PANW", "CRWD", "FTNT", "ZS", "NET", "SMCI", "ARM", "SNOW",
        "MDB", "DDOG", "AI", "PATH", "NOW"
    ],
    "China & Emerging Growth": [
        "BABA", "BIDU", "PDD", "JD", "NIO", "XPEV", "BYDDF", "TCEHY"
    ]
}

SECTOR_ETFS = {
    "Technologie (XLK)": "XLK",
    "Gesundheit (XLV)": "XLV",
    "Finanzen (XLF)": "XLF",
    "Konsum (XLY)": "XLY",
    "Energie (XLE)": "XLE",
    "Industrie (XLI)": "XLI"
}

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["AAPL", "MSFT", "NVDA", "SAP.DE"]

if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = "AAPL"

if 'nav_page' not in st.session_state:
    st.session_state.nav_page = "📊 Aktien-Analyse"

if 'risk_preset' not in st.session_state:
    st.session_state.risk_preset = {"ticker": None, "entry": None, "sl": None, "label": "Aktueller Kurs"}

def open_ticker_analysis(symbol: str):
    st.session_state.active_ticker = symbol
    st.session_state.nav_page = "📊 Aktien-Analyse"

# ==========================================
# CACHING & DATEN-LAYER
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_eur_exchange_rate(currency: str) -> float:
    if not currency or currency.upper() in ["EUR", "EUR="]:
        return 1.0
    curr = currency.upper()
    try:
        multiplier = 0.01 if currency == "GBp" else 1.0
        base_curr = "GBP" if currency == "GBp" else curr

        fx_data = yf.Ticker(f"{base_curr}EUR=X").history(period="1d")
        if not fx_data.empty:
            return float(fx_data['Close'].iloc[-1]) * multiplier

        inv_data = yf.Ticker(f"EUR{base_curr}=X").history(period="1d")
        if not inv_data.empty:
            return (1.0 / float(inv_data['Close'].iloc[-1])) * multiplier
    except Exception:
        pass
    return 1.0

@st.cache_data(ttl=900, show_spinner=False)
def load_stock_data(symbol: str):
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    df_daily = ticker.history(period="1y")
    cashflow_df = ticker.cashflow
    financials_df = ticker.financials
    balance_sheet_df = ticker.balance_sheet

    try:
        news_data = ticker.news or []
    except Exception:
        news_data = []

    try:
        calendar_data = ticker.calendar
    except Exception:
        calendar_data = None

    try:
        dividends_data = ticker.dividends
    except Exception:
        dividends_data = pd.Series(dtype=float)

    return info, df_daily, cashflow_df, financials_df, balance_sheet_df, news_data, calendar_data, dividends_data

@st.cache_data(ttl=600, show_spinner=False)
def load_chart_history(symbol: str, period: str, interval: str) -> pd.DataFrame:
    return yf.Ticker(symbol).history(period=period, interval=interval)

@st.cache_data(ttl=600, show_spinner=False)
def load_quick_quote(symbol: str) -> dict:
    try:
        t = yf.Ticker(symbol)
        inf = t.info or {}
        hist = t.history(period="1y")
        return {"symbol": symbol, "info": inf, "hist": hist, "error": None}
    except Exception as e:
        return {"symbol": symbol, "info": {}, "hist": pd.DataFrame(), "error": str(e)}

@st.cache_data(ttl=900, show_spinner=False)
def load_market_overview():
    sp500 = yf.Ticker("^GSPC").history(period="1y")
    vix = yf.Ticker("^VIX").history(period="5d")
    dax = yf.Ticker("^GDAXI").history(period="1y")
    sector_perf = []
    for name, sym in SECTOR_ETFS.items():
        try:
            h = yf.Ticker(sym).history(period="1mo")
            if len(h) >= 2:
                chg = ((h['Close'].iloc[-1] - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
                sector_perf.append({"Sektor": name, "Performance (%)": chg})
        except Exception:
            continue
    return sp500, vix, dax, sector_perf

@st.cache_data(ttl=600, show_spinner=False)
def search_ticker(query: str):
    if not query:
        return []
    try:
        results = yf.Search(query, max_results=6).quotes
        options = []
        for r in results:
            sym = r.get('symbol')
            name = r.get('shortname', r.get('longname', sym))
            exch = r.get('exchDisp', '')
            if sym:
                label = f"{name} ({sym}) - {exch}" if exch else f"{name} ({sym})"
                options.append((label, sym))
        return options
    except Exception:
        return []

# ==========================================
# EINSTIEGSZONEN-ENGINE (ATR, POC, FIB, VWAP)
# ==========================================
def analyze_entry_zones(df: pd.DataFrame, current_price: float) -> dict:
    if df is None or df.empty or len(df) < 50:
        return {"valid": False}

    work = df.copy()
    work['SMA_50'] = ta.trend.sma_indicator(work['Close'], window=50)
    work['SMA_200'] = ta.trend.sma_indicator(work['Close'], window=200) if len(work) >= 200 else work['SMA_50']
    work['RSI'] = ta.momentum.rsi(work['Close'], window=14)
    work['ATR'] = ta.volatility.average_true_range(work['High'], work['Low'], work['Close'], window=14)

    last_sma50 = float(work['SMA_50'].iloc[-1])
    last_sma200 = float(work['SMA_200'].iloc[-1])
    last_rsi = float(work['RSI'].iloc[-1]) if pd.notna(work['RSI'].iloc[-1]) else 50.0
    atr_14 = float(work['ATR'].iloc[-1]) if pd.notna(work['ATR'].iloc[-1]) else (current_price * 0.02)

    low_52 = float(work['Low'].min())
    high_52 = float(work['High'].max())
    low_52_idx = work['Low'].idxmin()

    sma50_low = last_sma50 - (0.5 * atr_14)
    sma50_high = last_sma50 + (0.5 * atr_14)
    sma200_low = last_sma200 - (0.5 * atr_14)
    sma200_high = last_sma200 + (0.5 * atr_14)

    fib_range = max(high_52 - low_52, 0.01)
    fib_382 = high_52 - (0.382 * fib_range)
    fib_500 = high_52 - (0.500 * fib_range)
    fib_618 = high_52 - (0.618 * fib_range)
    fib_650 = high_52 - (0.650 * fib_range)

    bins = np.linspace(low_52, high_52, 25)
    binned = pd.cut(work['Close'], bins=bins, include_lowest=True)
    vol_by_bin = work.groupby(binned, observed=False)['Volume'].sum()
    bin_mids = [iv.mid for iv in vol_by_bin.index]
    bin_vols = vol_by_bin.values.tolist()

    poc_idx = int(np.argmax(bin_vols)) if len(bin_vols) > 0 else 0
    poc_price = float(bin_mids[poc_idx]) if len(bin_mids) > 0 else last_sma200

    anchored_df = work.loc[low_52_idx:].copy()
    typical_price = (anchored_df['High'] + anchored_df['Low'] + anchored_df['Close']) / 3.0
    cum_vol = anchored_df['Volume'].cumsum().replace(0, np.nan)
    anchored_df['AVWAP'] = (typical_price * anchored_df['Volume']).cumsum() / cum_vol
    last_avwap = float(anchored_df['AVWAP'].iloc[-1]) if pd.notna(anchored_df['AVWAP'].iloc[-1]) else last_sma200

    suggested_sl_200 = max(0.01, sma200_low - (2.0 * atr_14))
    suggested_sl_curr = max(0.01, current_price - (2.0 * atr_14))

    confluence_hits = []
    if abs(current_price - last_sma200) <= atr_14:
        confluence_hits.append("200-SMA Support (±1 ATR)")
    if abs(current_price - last_sma50) <= atr_14:
        confluence_hits.append("50-SMA Trend-Support (±1 ATR)")
    if fib_650 <= current_price <= fib_382:
        confluence_hits.append("Fibonacci Korrekturzone (38.2%–65.0%)")
    if abs(current_price - poc_price) <= atr_14:
        confluence_hits.append("Volume Point of Control (POC)")
    if abs(current_price - last_avwap) <= atr_14:
        confluence_hits.append("Anchored VWAP (ab 52W-Tief)")
    if last_rsi < 40:
        confluence_hits.append(f"RSI abgekühlt ({last_rsi:.1f})")

    atr_dist_sma200 = (current_price - last_sma200) / atr_14 if atr_14 > 0 else 0.0

    return {
        "valid": True,
        "has_200": len(work) >= 200,
        "df": work,
        "avwap_series": anchored_df['AVWAP'],
        "last_avwap": last_avwap,
        "atr_14": atr_14,
        "last_sma50": last_sma50,
        "last_sma200": last_sma200,
        "last_rsi": last_rsi,
        "low_52": low_52,
        "high_52": high_52,
        "sma50_low": sma50_low,
        "sma50_high": sma50_high,
        "sma200_low": sma200_low,
        "sma200_high": sma200_high,
        "fib_382": fib_382,
        "fib_500": fib_500,
        "fib_618": fib_618,
        "fib_650": fib_650,
        "poc_price": poc_price,
        "vp_mids": bin_mids,
        "vp_vols": bin_vols,
        "suggested_sl_200": suggested_sl_200,
        "suggested_sl_curr": suggested_sl_curr,
        "confluence_hits": confluence_hits,
        "confluence_count": len(confluence_hits),
        "atr_dist_sma200": atr_dist_sma200,
    }

def get_days_to_earnings(calendar_data) -> int | None:
    if calendar_data is None or (isinstance(calendar_data, pd.DataFrame) and calendar_data.empty):
        return None
    try:
        cal_dict = calendar_data if isinstance(calendar_data, dict) else calendar_data.to_dict()
        raw_date = cal_dict.get('Earnings Date', [None])[0] if isinstance(cal_dict.get('Earnings Date'), list) else cal_dict.get('Earnings Date')
        if raw_date is None:
            return None
        if isinstance(raw_date, datetime.datetime):
            e_dt = raw_date.date()
        elif isinstance(raw_date, datetime.date):
            e_dt = raw_date
        else:
            e_dt = pd.to_datetime(str(raw_date)).date()
        diff = (e_dt - datetime.date.today()).days
        return diff if diff >= 0 else None
    except Exception:
        return None

# ==========================================
# FINANZMATHEMATIK & SCORING
# ==========================================
def calculate_dcf(fcf_millions: float, net_debt_millions: float, shares_millions: float,
                  growth_y1_5: float = 0.10, growth_y6_10: float = 0.05,
                  wacc: float = 0.09, terminal_multiple: float = 15.0) -> float:
    if shares_millions <= 0 or fcf_millions <= 0:
        return 0.0
    disc_fcf_sum = 0.0
    p_fcf = fcf_millions
    for y in range(1, 11):
        r = growth_y1_5 if y <= 5 else growth_y6_10
        p_fcf *= (1 + r)
        disc_fcf_sum += p_fcf / ((1 + wacc) ** y)

    tv = p_fcf * terminal_multiple
    disc_tv = tv / ((1 + wacc) ** 10)
    eq_val = (disc_fcf_sum + disc_tv) - net_debt_millions
    return max(0.0, eq_val / shares_millions)

def _get_row_val(df: pd.DataFrame, keys: list, col_idx: int = 0, default=None):
    if df is None or df.empty:
        return default
    for k in keys:
        if k in df.index and len(df.columns) > col_idx:
            val = df.loc[k].iloc[col_idx]
            if pd.notna(val):
                return float(val)
    return default

def calculate_piotroski_score(financials: pd.DataFrame, balance_sheet: pd.DataFrame, cashflow: pd.DataFrame):
    score = 0
    details = []
    if financials is None or financials.empty or balance_sheet is None or balance_sheet.empty or cashflow is None or cashflow.empty:
        return 0, [("🟡 Info", "Unvollständige Bilanzen für Piotroski F-Score")]

    net_inc = _get_row_val(financials, ['Net Income'], 0, 0)
    net_inc_prev = _get_row_val(financials, ['Net Income'], 1, 0)
    ocf = _get_row_val(cashflow, ['Operating Cash Flow', 'Total Cash From Operating Activities'], 0, 0)
    tot_assets = _get_row_val(balance_sheet, ['Total Assets'], 0, 0)
    tot_assets_prev = _get_row_val(balance_sheet, ['Total Assets'], 1, 0)

    if net_inc > 0:
        score += 1
        details.append(("🟢 F1 - Nettogewinn", f"Positiv ({net_inc/1e6:,.0f} Mio.)"))
    else:
        details.append(("🔴 F1 - Nettogewinn", "Negativ"))

    if ocf > 0:
        score += 1
        details.append(("🟢 F2 - Operativer Cashflow", f"Positiv ({ocf/1e6:,.0f} Mio.)"))
    else:
        details.append(("🔴 F2 - Operativer Cashflow", "Negativ"))

    roa_curr = (net_inc / tot_assets) if tot_assets else 0
    roa_prev = (net_inc_prev / tot_assets_prev) if tot_assets_prev else 0
    if roa_curr > roa_prev:
        score += 1
        details.append(("🟢 F3 - ROA Dynamik", f"Gestiegen ({roa_curr*100:.1f}% vs. {roa_prev*100:.1f}%)"))
    else:
        details.append(("🔴 F3 - ROA Dynamik", f"Gesunken/Stagniert ({roa_curr*100:.1f}% vs. {roa_prev*100:.1f}%)"))

    if ocf > net_inc:
        score += 1
        details.append(("🟢 F4 - Gewinnqualität", "Operativer Cashflow > Bilanzgewinn"))
    else:
        details.append(("🔴 F4 - Gewinnqualität", "Bilanzgewinn > Operativer Cashflow"))

    lt_debt = _get_row_val(balance_sheet, ['Long Term Debt'], 0, 0)
    lt_debt_prev = _get_row_val(balance_sheet, ['Long Term Debt'], 1, 0)
    debt_ratio_curr = (lt_debt / tot_assets) if tot_assets else 0
    debt_ratio_prev = (lt_debt_prev / tot_assets_prev) if tot_assets_prev else 0
    if debt_ratio_curr <= debt_ratio_prev:
        score += 1
        details.append(("🟢 F5 - Verschuldungsgrad", "Langfristige Schuldenquote gesunken/stabil"))
    else:
        details.append(("🔴 F5 - Verschuldungsgrad", "Langfristige Schuldenquote gestiegen"))

    curr_assets = _get_row_val(balance_sheet, ['Current Assets', 'Total Current Assets'], 0, 0)
    curr_liab = _get_row_val(balance_sheet, ['Current Liabilities', 'Total Current Liabilities'], 0, 0)
    curr_assets_prev = _get_row_val(balance_sheet, ['Current Assets', 'Total Current Assets'], 1, 0)
    curr_liab_prev = _get_row_val(balance_sheet, ['Current Liabilities', 'Total Current Liabilities'], 1, 0)
    cr_curr = (curr_assets / curr_liab) if curr_liab else 0
    cr_prev = (curr_assets_prev / curr_liab_prev) if curr_liab_prev else 0
    if cr_curr > cr_prev:
        score += 1
        details.append(("🟢 F6 - Liquidität (Current Ratio)", f"Verbessert ({cr_curr:.2f} vs. {cr_prev:.2f})"))
    else:
        details.append(("🔴 F6 - Liquidität (Current Ratio)", f"Gesunken ({cr_curr:.2f} vs. {cr_prev:.2f})"))

    shares_curr = _get_row_val(balance_sheet, ['Ordinary Shares Number', 'Share Issued'], 0, 0)
    shares_prev = _get_row_val(balance_sheet, ['Ordinary Shares Number', 'Share Issued'], 1, 0)
    if shares_curr <= shares_prev or shares_prev == 0:
        score += 1
        details.append(("🟢 F7 - Aktienanzahl", "Keine Verwässerung (Anzahl stabil/gesunken)"))
    else:
        details.append(("🔴 F7 - Aktienanzahl", "Neue Aktien ausgegeben (Verwässerung)"))

    gp_curr = _get_row_val(financials, ['Gross Profit'], 0, 0)
    rev_curr = _get_row_val(financials, ['Total Revenue'], 0, 0)
    gp_prev = _get_row_val(financials, ['Gross Profit'], 1, 0)
    rev_prev = _get_row_val(financials, ['Total Revenue'], 1, 0)
    gm_curr = (gp_curr / rev_curr) if rev_curr else 0
    gm_prev = (gp_prev / rev_prev) if rev_prev else 0
    if gm_curr > gm_prev:
        score += 1
        details.append(("🟢 F8 - Bruttomarge", f"Gestiegen ({gm_curr*100:.1f}% vs. {gm_prev*100:.1f}%)"))
    else:
        details.append(("🔴 F8 - Bruttomarge", f"Gesunken ({gm_curr*100:.1f}% vs. {gm_prev*100:.1f}%)"))

    at_curr = (rev_curr / tot_assets) if tot_assets else 0
    at_prev = (rev_prev / tot_assets_prev) if tot_assets_prev else 0
    if at_curr > at_prev:
        score += 1
        details.append(("🟢 F9 - Kapitalumschlag", f"Effizienz gestiegen ({at_curr:.2f}x vs. {at_prev:.2f}x)"))
    else:
        details.append(("🔴 F9 - Kapitalumschlag", f"Effizienz gesunken ({at_curr:.2f}x vs. {at_prev:.2f}x)"))

    return score, details

# ==========================================
# PDF-REPORT GENERATOR
# ==========================================
def generate_pdf_report(symbol, company_name, current_price, fair_value, score, piotroski_score, reasons, currency_symbol, eur_rate, entry_data=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1E1E1E"))
    story.append(Paragraph(f"Aktienanalyse-Report: {company_name} ({symbol})", title_style))
    story.append(Spacer(1, 12))

    data = [
        ["Metrik", "Wert (Original)", "Wert (EUR €)"],
        ["Aktueller Kurs", f"{current_price:.2f} {currency_symbol}", f"{current_price * eur_rate:.2f} €"],
        ["DCF Fairer Wert", f"{fair_value:.2f} {currency_symbol}" if fair_value > 0 else "N/A (Neg. FCF)", f"{fair_value * eur_rate:.2f} €" if fair_value > 0 else "-"],
        ["Gesamt-Score", f"{score} / 6 Punkte", "-"],
        ["Piotroski F-Score", f"{piotroski_score} / 9 Punkte", "-"]
    ]

    if entry_data and entry_data.get("valid"):
        data.append(["Volume POC (Haupt-Support)", f"{entry_data['poc_price']:.2f} {currency_symbol}", f"{entry_data['poc_price'] * eur_rate:.2f} €"])
        data.append(["200-SMA ATR-Kaufzone", f"{entry_data['sma200_low']:.2f} - {entry_data['sma200_high']:.2f} {currency_symbol}", f"{entry_data['sma200_low']*eur_rate:.2f} - {entry_data['sma200_high']*eur_rate:.2f} €"])
        data.append(["ATR Stop-Loss (200-SMA)", f"{entry_data['suggested_sl_200']:.2f} {currency_symbol}", f"{entry_data['suggested_sl_200'] * eur_rate:.2f} €"])

    t = Table(data, colWidths=[160, 150, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0E1117")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    story.append(t)
    story.append(Spacer(1, 18))

    story.append(Paragraph("<b>Detail-Bewertungen:</b>", styles['Heading2']))
    for status, text in reasons:
        clean_status = status.encode('ascii', 'ignore').decode('ascii').strip()
        story.append(Paragraph(f"• <b>{clean_status}:</b> {text}", styles['Normal']))
        story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# SEITENLEISTE: SUCHE, NAVIGATION & FAVORITEN
# ==========================================
with st.sidebar:
    st.markdown("## 🤑 GEILEPROFITE")

    # Kompakte Schnellsuche direkt in der Sidebar
    quick_query = st.text_input(
        "Aktie suchen",
        placeholder="Name oder Ticker (z. B. NVDA, SAP.DE)...",
        label_visibility="collapsed"
    )
    if quick_query:
        matches = search_ticker(quick_query)
        if matches:
            chosen = st.selectbox(
                "Treffer auswählen:",
                options=[m[0] for m in matches],
                label_visibility="collapsed"
            )
            for lbl, sym in matches:
                if lbl == chosen and st.session_state.active_ticker != sym:
                    open_ticker_analysis(sym)
                    st.rerun()
        else:
            if st.button(f"Direkt laden: {quick_query.strip().upper()}", use_container_width=True):
                open_ticker_analysis(quick_query.strip().upper())
                st.rerun()

    st.markdown("---")

    nav_options = ["📊 Aktien-Analyse", "🔍 Aktien-Screener", "⭐ Watchlist", "🌐 Markt & Stimmung"]
    current_idx = nav_options.index(st.session_state.nav_page) if st.session_state.nav_page in nav_options else 0
    selected_nav = st.radio("Ansicht", nav_options, index=current_idx, label_visibility="collapsed")
    if selected_nav != st.session_state.nav_page:
        st.session_state.nav_page = selected_nav
        st.rerun()

    st.markdown("---")

    if st.session_state.watchlist:
        st.markdown("#### ⭐ Schnellzugriff")
        with ThreadPoolExecutor(max_workers=6) as executor:
            fav_results = list(executor.map(load_quick_quote, st.session_state.watchlist[:8]))

        for item in fav_results:
            w_sym = item["symbol"]
            w_inf = item["info"]
            w_curr = w_inf.get('currency', 'USD')
            w_rate = get_eur_exchange_rate(w_curr)
            price_val = w_inf.get('currentPrice') or w_inf.get('regularMarketPrice') or 0
            prev_close = w_inf.get('previousClose') or price_val

            if price_val and prev_close:
                change_pct = ((price_val - prev_close) / prev_close) * 100
                price_eur = price_val * w_rate
                icon = "🟢" if change_pct >= 0 else "🔴"
                label_str = f"{w_sym} · {price_eur:.2f} € ({icon} {change_pct:+.1f}%)"
            else:
                label_str = f"{w_sym}"

            if st.button(label_str, key=f"fav_btn_{w_sym}", use_container_width=True):
                open_ticker_analysis(w_sym)
                st.rerun()

main_nav = st.session_state.nav_page

# ==========================================
# ANSICHT 1: AKTIEN-ANALYSE (5 KLARE TABS)
# ==========================================
if main_nav == "📊 Aktien-Analyse":
    ticker_symbol = st.session_state.active_ticker

    try:
        with st.spinner(f"Lade Analyse für {ticker_symbol}..."):
            info, df_daily, cashflow_df, financials_df, balance_sheet_df, news_data, calendar_data, dividends_data = load_stock_data(ticker_symbol)

        if not info or (not info.get('regularMarketPrice') and not info.get('currentPrice') and df_daily.empty):
            st.error(f"Keine gültigen Marktdaten für **{ticker_symbol}** gefunden. Bitte überprüfe das Ticker-Symbol (z. B. `SAP.DE` für Xetra).")
            st.stop()

        company_name = info.get('longName', ticker_symbol)
        raw_currency = info.get('currency', 'USD')
        currency_code = raw_currency.upper()
        curr_symbol = "$" if currency_code == "USD" else ("€" if currency_code == "EUR" else currency_code)
        eur_rate = get_eur_exchange_rate(raw_currency)

        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or (df_daily['Close'].iloc[-1] if not df_daily.empty else 0)
        prev_close = info.get('previousClose') or current_price
        day_chg_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0.0

        # Einstiegszonen & Fundamentaldaten vorab berechnen
        entry_data = analyze_entry_zones(df_daily, current_price)
        has_tech_data = entry_data["valid"] and entry_data["has_200"]

        if entry_data["valid"]:
            df_daily = entry_data["df"]
            last_close = df_daily['Close'].iloc[-1]
            last_sma50 = entry_data["last_sma50"]
            last_sma200 = entry_data["last_sma200"]
            last_rsi = entry_data["last_rsi"]
        else:
            last_close = current_price
            last_sma50 = last_sma200 = last_rsi = 0

        raw_fcf = _get_row_val(cashflow_df, ['Free Cash Flow'], 0, 0)
        free_cash_flow_m = raw_fcf / 1e6 if raw_fcf else 0.0
        shares_outstanding_m = (info.get('sharesOutstanding') or 0) / 1e6
        total_debt_m = (info.get('totalDebt') or 0) / 1e6
        total_cash_m = (info.get('totalCash') or 0) / 1e6
        net_debt_m = total_debt_m - total_cash_m

        dcf_fair_value = calculate_dcf(free_cash_flow_m, net_debt_m, shares_outstanding_m)
        dcf_margin = ((dcf_fair_value - current_price) / current_price) * 100 if (current_price and dcf_fair_value > 0) else 0
        piotroski_score, piotroski_details = calculate_piotroski_score(financials_df, balance_sheet_df, cashflow_df)

        # Basis-Score (0–6)
        score = 0
        max_score = 6
        reasons = []

        if has_tech_data:
            if last_close > last_sma200:
                score += 1
                reasons.append(("🟢 Positiv", "Kurs über SMA 200 (Langfristiger Aufwärtstrend)"))
            else:
                reasons.append(("🔴 Negativ", "Kurs unter SMA 200 (Langfristiger Abwärtstrend)"))

            if last_rsi < 35:
                score += 1
                reasons.append(("🟢 Positiv", f"RSI bei {last_rsi:.1f} (Überverkauft – potenzielle Kaufchance)"))
            elif last_rsi > 65:
                reasons.append(("🔴 Negativ", f"RSI bei {last_rsi:.1f} (Überkauft)"))
            else:
                reasons.append(("🟡 Neutral", f"RSI im neutralen Bereich ({last_rsi:.1f})"))

            if last_sma50 > last_sma200:
                score += 1
                reasons.append(("🟢 Positiv", "Golden Cross aktiv (SMA 50 > SMA 200)"))
            else:
                reasons.append(("🔴 Negativ", "Death Cross aktiv (SMA 50 < SMA 200)"))
        else:
            reasons.append(("🟡 Hinweis", "Weniger als 200 Handelstage verfügbar (Technische Punkte entfallen)"))

        forward_pe = info.get('forwardPE')
        if forward_pe and 0 < forward_pe < 20:
            score += 1
            reasons.append(("🟢 Positiv", f"Moderates Forward-KGV ({forward_pe:.1f})"))
        elif forward_pe:
            reasons.append(("🟡 Neutral/Teuer", f"Erhöhtes Forward-KGV ({forward_pe:.1f})"))
        else:
            reasons.append(("🟡 Neutral", "Kein Forward-KGV verfügbar"))

        margin_val = info.get('profitMargins')
        if margin_val and margin_val > 0.15:
            score += 1
            reasons.append(("🟢 Positiv", f"Starke Nettomarge ({margin_val*100:.1f}%)"))
        else:
            reasons.append(("🔴 Negativ", "Geringe oder negative Nettomarge (< 15%)"))

        roe_val = info.get('returnOnEquity')
        if roe_val and roe_val > 0.15:
            score += 1
            reasons.append(("🟢 Positiv", f"Hohe Eigenkapitalrendite ({roe_val*100:.1f}%)"))
        else:
            reasons.append(("🔴 Negativ", "Schwache Eigenkapitalrendite (< 15%)"))

        # ==========================================
        # KOMPAKTER HEADER MIT AKTIONEN
        # ==========================================
        h_left, h_right = st.columns([3.2, 1.3])
        with h_left:
            st.markdown(
                f"## {company_name} <span style='color:#8b949e; font-size:19px;'>({info.get('symbol', ticker_symbol)})</span>",
                unsafe_allow_html=True
            )
            st.caption(f"{info.get('sector', 'N/A')} · {info.get('industry', 'N/A')} · Währung: {raw_currency}")

        with h_right:
            act_c1, act_c2 = st.columns(2)
            with act_c1:
                in_wl = ticker_symbol in st.session_state.watchlist
                wl_btn_label = "★ Gespeichert" if in_wl else "⭐ Merken"
                if st.button(wl_btn_label, use_container_width=True):
                    if in_wl:
                        st.session_state.watchlist.remove(ticker_symbol)
                    else:
                        st.session_state.watchlist.append(ticker_symbol)
                    st.rerun()
            with act_c2:
                pdf_bytes = generate_pdf_report(
                    ticker_symbol, company_name, current_price, dcf_fair_value,
                    score, piotroski_score, reasons, curr_symbol, eur_rate, entry_data
                )
                st.download_button(
                    "📄 PDF",
                    data=pdf_bytes,
                    file_name=f"{ticker_symbol}_Analyse.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        # ==========================================
        # KOMPAKTE 4ER-ÜBERSICHTSLEISTE
        # ==========================================
        k1, k2, k3, k4 = st.columns(4)

        with k1:
            price_eur = current_price * eur_rate
            if currency_code != "EUR":
                st.metric("Aktueller Kurs", f"{price_eur:.2f} €", delta=f"{current_price:.2f} {curr_symbol} ({day_chg_pct:+.2f}%)")
            else:
                st.metric("Aktueller Kurs", f"{current_price:.2f} €", delta=f"{day_chg_pct:+.2f}% heute")

        with k2:
            if score >= 5:
                st.markdown(f"<div class='verdict-box verdict-buy'><div class='verdict-label'>Gesamt-Urteil ({score}/{max_score} Pkt.)</div><div class='verdict-value' style='color:#2ea043;'>KAUFSIGNAL</div><div class='verdict-sub'>Piotroski Quality: {piotroski_score}/9</div></div>", unsafe_allow_html=True)
            elif score >= 3:
                st.markdown(f"<div class='verdict-box verdict-hold'><div class='verdict-label'>Gesamt-Urteil ({score}/{max_score} Pkt.)</div><div class='verdict-value' style='color:#d29922;'>HALTEN / BEOBACHTEN</div><div class='verdict-sub'>Piotroski Quality: {piotroski_score}/9</div></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='verdict-box verdict-sell'><div class='verdict-label'>Gesamt-Urteil ({score}/{max_score} Pkt.)</div><div class='verdict-value' style='color:#f85149;'>VORSICHT / MEIDEN</div><div class='verdict-sub'>Piotroski Quality: {piotroski_score}/9</div></div>", unsafe_allow_html=True)

        with k3:
            if dcf_fair_value > 0:
                dcf_eur = dcf_fair_value * eur_rate
                st.metric("DCF Fairer Wert", f"{dcf_eur:.2f} €", delta=f"{dcf_margin:+.1f}% vs. Kurs")
            else:
                st.metric("DCF Fairer Wert", "N/A", delta="Negativer FCF", delta_color="off")

        with k4:
            if entry_data["valid"]:
                poc_eur = entry_data["poc_price"] * eur_rate
                conf_cnt = entry_data["confluence_count"]
                st.metric("Haupt-Support (POC)", f"{poc_eur:.2f} €", delta=f"{conf_cnt} Einstiegs-Faktoren aktiv")
            else:
                kgv_str = f"{forward_pe:.1f}" if isinstance(forward_pe, (int, float)) else "N/A"
                st.metric("Forward KGV", kgv_str)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # ==========================================
        # 5 THEMEN-TABS STATT 10 EINZEL-TABS
        # ==========================================
        tab_overview, tab_valuation, tab_fundamentals, tab_div_peers, tab_news = st.tabs([
            "📈 Chart & Einstiegszonen",
            "🧮 Bewertung & Risiko",
            "🏛️ Fundamental & Quality",
            "💰 Dividende & Peers",
            "📰 News & Termine"
        ])

        # ------------------------------------------
        # TAB 1: CHART & MULTI-FAKTOR EINSTIEGSZONEN
        # ------------------------------------------
        with tab_overview:
            days_to_earn = get_days_to_earnings(calendar_data)
            if days_to_earn is not None and days_to_earn <= 7:
                st.warning(f"⚠️ **Earnings-Hinweis:** In **{days_to_earn} Tag(en)** werden Quartalszahlen veröffentlicht. Technische Kaufzonen können durch Kurs-Gaps übersprungen werden.")

            view_mode = st.radio(
                "Ansicht wählen:",
                ["🎯 Einstiegszonen & Volume Profile (1 Jahr)", "🕯️ Interaktiver Candlestick-Chart"],
                horizontal=True,
                label_visibility="collapsed"
            )

            if view_mode == "🎯 Einstiegszonen & Volume Profile (1 Jahr)":
                if entry_data["valid"]:
                    atr_14 = entry_data["atr_14"]
                    poc_price = entry_data["poc_price"]
                    last_avwap = entry_data["last_avwap"]
                    sma50_low, sma50_high = entry_data["sma50_low"], entry_data["sma50_high"]
                    sma200_low, sma200_high = entry_data["sma200_low"], entry_data["sma200_high"]
                    fib_618, fib_650 = entry_data["fib_618"], entry_data["fib_650"]
                    suggested_sl_200 = entry_data["suggested_sl_200"]
                    confluence_hits = entry_data["confluence_hits"]

                    ez_col1, ez_col2 = st.columns([1, 1.55])

                    with ez_col1:
                        if len(confluence_hits) >= 2:
                            st.success(f"**🔥 Starke Einstiegs-Konfluenz ({len(confluence_hits)} Faktoren):**\n- " + "\n- ".join(confluence_hits))
                        elif len(confluence_hits) == 1:
                            st.info(f"**⚡ Moderater Support aktiv:** {confluence_hits[0]}")
                        else:
                            st.info(f"**⏳ Aktuell frei im Trend:** Abstand zum 200-SMA beträgt `{entry_data['atr_dist_sma200']:+.1f}x ATR` (Tages-ATR: `{atr_14:.2f} {curr_symbol}`).")

                        st.markdown(f"""
                        **Gestaffelter Tranchen-Plan:**
                        * **1. Trend-Rücksetzer (50-SMA):**  
                          `{sma50_low*eur_rate:.2f} – {sma50_high*eur_rate:.2f} €` *({sma50_low:.2f}–{sma50_high:.2f} {curr_symbol})*
                        * **2. Golden Pocket (Fib 61.8–65%):**  
                          `{fib_650*eur_rate:.2f} – {fib_618*eur_rate:.2f} €` *({fib_650:.2f}–{fib_618:.2f} {curr_symbol})*
                        * **3. Haupt-Kaufzone (200-SMA):**  
                          `{sma200_low*eur_rate:.2f} – {sma200_high*eur_rate:.2f} €` *({sma200_low:.2f}–{sma200_high:.2f} {curr_symbol})*
                        * **Anchored VWAP:** `{last_avwap*eur_rate:.2f} €` · **ATR Stop-Loss:** `{suggested_sl_200*eur_rate:.2f} €`
                        """)

                        st.markdown("**Schnell-Übergabe in den Positionsrechner:**")
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("📌 Markt-Einstieg + ATR-SL", use_container_width=True):
                                st.session_state.risk_preset = {
                                    "ticker": ticker_symbol,
                                    "entry": float(current_price),
                                    "sl": float(entry_data["suggested_sl_curr"]),
                                    "label": "Aktueller Kurs (2x ATR Stop)"
                                }
                                st.toast("Im Tab 'Bewertung & Risiko' hinterlegt!")
                        with b2:
                            if st.button("🎯 200-SMA Limit + ATR-SL", use_container_width=True):
                                st.session_state.risk_preset = {
                                    "ticker": ticker_symbol,
                                    "entry": float(last_sma200),
                                    "sl": float(suggested_sl_200),
                                    "label": "200-SMA Limit-Order (2x ATR Stop)"
                                }
                                st.toast("200-SMA Limit im Tab 'Bewertung & Risiko' hinterlegt!")

                    with ez_col2:
                        fig_entry = make_subplots(
                            rows=1, cols=2,
                            shared_yaxes=True,
                            column_widths=[0.83, 0.17],
                            horizontal_spacing=0.01
                        )
                        df_e = entry_data["df"]
                        avwap_s = entry_data["avwap_series"]

                        fig_entry.add_trace(go.Scatter(x=df_e.index, y=df_e['Close'], mode='lines', name='Kurs', line=dict(color='#e6edf3', width=1.8)), row=1, col=1)
                        fig_entry.add_trace(go.Scatter(x=df_e.index, y=df_e['SMA_50'], mode='lines', name='50-SMA', line=dict(color='#58a6ff', width=1.2)), row=1, col=1)
                        if entry_data["has_200"]:
                            fig_entry.add_trace(go.Scatter(x=df_e.index, y=df_e['SMA_200'], mode='lines', name='200-SMA', line=dict(dash='dash', color='#f59e0b', width=1.5)), row=1, col=1)
                        fig_entry.add_trace(go.Scatter(x=avwap_s.index, y=avwap_s, mode='lines', name='Anchored VWAP', line=dict(color='#39d353', width=1.4, dash='dot')), row=1, col=1)

                        fig_entry.add_hrect(y0=sma200_low, y1=sma200_high, fillcolor="#2ea043", opacity=0.18, line_width=0, annotation_text="200-SMA Zone", annotation_position="bottom left", row=1, col=1)
                        fig_entry.add_hrect(y0=fib_650, y1=fib_618, fillcolor="#a371f7", opacity=0.15, line_width=0, annotation_text="Golden Pocket", annotation_position="top left", row=1, col=1)
                        fig_entry.add_hline(y=poc_price, line_dash="dot", line_color="#3fb950", annotation_text=f"POC ({poc_price:.1f})", row=1, col=1)

                        vp_colors = ['#3fb950' if abs(m - poc_price) < 1e-6 else 'rgba(139, 148, 158, 0.35)' for m in entry_data["vp_mids"]]
                        fig_entry.add_trace(go.Bar(
                            x=entry_data["vp_vols"],
                            y=entry_data["vp_mids"],
                            orientation='h',
                            marker_color=vp_colors,
                            showlegend=False
                        ), row=1, col=2)

                        fig_entry.update_layout(
                            template="plotly_dark",
                            height=440,
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            margin=dict(l=10, r=10, t=25, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
                        )
                        fig_entry.update_xaxes(showticklabels=False, showgrid=False, row=1, col=2)
                        st.plotly_chart(fig_entry, use_container_width=True)
                else:
                    st.info("Für die Einstiegszonen-Analyse werden mindestens 50 Handelstage benötigt.")

            else:
                c_tf1, c_tf2, c_tf3 = st.columns([1, 1, 1])
                with c_tf1:
                    timeframe = st.selectbox("Zeitraum:", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=5)
                with c_tf2:
                    if timeframe == "1d":
                        interval_options, default_idx = ["1m", "2m", "5m", "15m", "30m", "60m"], 2
                    elif timeframe == "5d":
                        interval_options, default_idx = ["5m", "15m", "30m", "60m", "1d"], 1
                    else:
                        interval_options, default_idx = ["1d", "1wk", "1mo"], 0
                    interval = st.selectbox("Intervall:", interval_options, index=default_idx)
                with c_tf3:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    show_bb = st.checkbox("Bollinger Bänder & SMA 50", value=True)

                hist = load_chart_history(ticker_symbol, timeframe, interval)
                if not hist.empty:
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.72, 0.28])
                    fig.add_trace(go.Candlestick(
                        x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
                        name=f"Kurs ({curr_symbol})"
                    ), row=1, col=1)

                    if show_bb and len(hist) >= 20:
                        bb = ta.volatility.BollingerBands(close=hist['Close'], window=20, window_dev=2)
                        fig.add_trace(go.Scatter(x=hist.index, y=bb.bollinger_hband(), line=dict(color='rgba(255,255,255,0.3)', width=1), name="BB Oben"), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=bb.bollinger_lband(), line=dict(color='rgba(255,255,255,0.3)', width=1), fill='tonexty', fillcolor='rgba(255,255,255,0.05)', name="BB Unten"), row=1, col=1)
                        if len(hist) >= 50:
                            fig.add_trace(go.Scatter(x=hist.index, y=ta.trend.sma_indicator(hist['Close'], 50), line=dict(color='#58a6ff', width=1.2), name="SMA 50"), row=1, col=1)

                    if len(hist) >= 26:
                        macd = ta.trend.MACD(close=hist['Close'])
                        macd_diff = macd.macd_diff()
                        fig.add_trace(go.Scatter(x=hist.index, y=macd.macd(), line=dict(color='#58a6ff', width=1.2), name="MACD"), row=2, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=macd.macd_signal(), line=dict(color='#f59e0b', width=1.2), name="Signal"), row=2, col=1)
                        colors_macd = ['#10b981' if val >= 0 else '#ef4444' for val in macd_diff.fillna(0)]
                        fig.add_trace(go.Bar(x=hist.index, y=macd_diff, marker_color=colors_macd, name="Hist"), row=2, col=1)

                    fig.update_layout(
                        xaxis_rangeslider_visible=False, template="plotly_dark", height=520,
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=20, b=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Keine Intraday-Daten für diese Auswahl verfügbar.")

        # ------------------------------------------
        # TAB 2: BEWERTUNG (DCF) & POSITIONSRECHNER
        # ------------------------------------------
        with tab_valuation:
            val_col1, val_col2 = st.columns([1, 1], gap="large")

            with val_col1:
                st.subheader("🧮 Fairer Wert (DCF-Simulation)")
                if free_cash_flow_m <= 0:
                    st.warning("Kein positiver Free Cash Flow vorhanden – FCF-basierte DCF-Bewertung nicht anwendbar.")
                else:
                    g_1_5 = st.slider("FCF-Wachstum Jahre 1–5 (% p.a.):", -5.0, 30.0, 10.0, 0.5) / 100
                    g_6_10 = st.slider("FCF-Wachstum Jahre 6–10 (% p.a.):", 0.0, 15.0, 5.0, 0.5) / 100
                    wacc_in = st.slider("Diskontierungssatz / WACC (%):", 5.0, 15.0, 9.0, 0.5) / 100
                    term_mult = st.slider("Terminal FCF-Multiple (Jahr 10):", 8.0, 25.0, 15.0, 1.0)

                    sim_fair_val = calculate_dcf(free_cash_flow_m, net_debt_m, shares_outstanding_m, g_1_5, g_6_10, wacc_in, term_mult)
                    sim_margin = ((sim_fair_val - current_price) / current_price) * 100 if current_price else 0

                    r_c1, r_c2 = st.columns(2)
                    r_c1.metric("Fairer Wert (EUR)", f"{sim_fair_val * eur_rate:.2f} €", delta=f"{sim_margin:+.1f}% vs. Kurs")
                    r_c2.metric("Fairer Wert (Orig.)", f"{sim_fair_val:.2f} {curr_symbol}")
                    st.caption(f"Basis: Free Cash Flow {free_cash_flow_m:,.0f} Mio. {curr_symbol} · Nettoverschuldung {net_debt_m:,.0f} Mio. {curr_symbol}")

            with val_col2:
                st.subheader("🛡️ Positionsgrößen- & Risiko-Rechner")
                preset = st.session_state.risk_preset
                use_preset = preset.get("ticker") == ticker_symbol and preset.get("entry") is not None

                default_entry = preset["entry"] if use_preset else float(current_price)
                default_sl = preset["sl"] if use_preset else (float(entry_data["suggested_sl_curr"]) if entry_data["valid"] else max(0.01, float(current_price * 0.95)))

                if use_preset:
                    st.caption(f"Übernommenes Szenario: **{preset['label']}**")

                account_size_eur = st.number_input("Depotkapital (€):", value=10000.0, step=1000.0, min_value=100.0)
                risk_pct = st.slider("Max. Risiko pro Trade (%):", 0.5, 5.0, 1.0, 0.5) / 100

                in_c1, in_c2 = st.columns(2)
                with in_c1:
                    entry_price_curr = st.number_input(f"Einstiegskurs ({curr_symbol}):", value=max(0.01, default_entry), step=1.0, min_value=0.01, key=f"entry_in_{ticker_symbol}_{default_entry:.2f}")
                with in_c2:
                    stop_loss_curr = st.number_input(f"Stop-Loss ({curr_symbol}):", value=max(0.01, default_sl), step=1.0, min_value=0.01, key=f"sl_in_{ticker_symbol}_{default_sl:.2f}")

                risk_amount_eur = account_size_eur * risk_pct
                risk_per_share_curr = entry_price_curr - stop_loss_curr
                risk_per_share_eur = risk_per_share_curr * eur_rate

                if risk_per_share_curr > 0 and risk_per_share_eur > 0:
                    position_shares = int(risk_amount_eur / risk_per_share_eur)
                    position_value_eur = position_shares * entry_price_curr * eur_rate
                    stop_dist_pct = (risk_per_share_curr / entry_price_curr) * 100

                    out_c1, out_c2 = st.columns(2)
                    out_c1.metric("Kaufmenge", f"{position_shares} Aktien", delta=f"Volumen: {position_value_eur:,.0f} €", delta_color="off")
                    out_c2.metric("Max. Verlust (Stop)", f"{risk_amount_eur:,.2f} €", delta=f"Abstand: -{stop_dist_pct:.1f}%", delta_color="off")
                else:
                    st.error("Der Stop-Loss muss unter dem Einstiegskurs liegen.")

        # ------------------------------------------
        # TAB 3: FUNDAMENTAL, QUALITY & BILANZEN
        # ------------------------------------------
        with tab_fundamentals:
            # Analysten-Leiste
            t_low = info.get('targetLowPrice')
            t_mean = info.get('targetMeanPrice')
            t_high = info.get('targetHighPrice')
            rec = (info.get('recommendationKey') or 'N/A').upper()
            num_analysts = info.get('numberOfAnalystOpinions', 'N/A')

            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Analysten-Konsens", rec, delta=f"{num_analysts} Meinungen" if num_analysts != 'N/A' else None)
            a2.metric("Kursziel Schnitt", f"{t_mean*eur_rate:.2f} €" if isinstance(t_mean, (int, float)) else "N/A", delta=f"{t_mean:.2f} {curr_symbol}" if isinstance(t_mean, (int, float)) else None, delta_color="off")
            a3.metric("Nettomarge", f"{(margin_val or 0)*100:.1f}%" if margin_val is not None else "N/A")
            a4.metric("Eigenkapitalrendite (ROE)", f"{(roe_val or 0)*100:.1f}%" if roe_val is not None else "N/A")

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            f_col1, f_col2 = st.columns(2)
            with f_col1:
                st.subheader(f"🚦 Basis-Check ({score} / {max_score})")
                for status, text in reasons:
                    st.write(f"- **{status}:** {text}")
            with f_col2:
                st.subheader(f"🏛️ Piotroski F-Score ({piotroski_score} / 9)")
                for status, text in piotroski_details:
                    st.write(f"- **{status}:** {text}")

            with st.expander("📑 Detaillierte Finanzberichte (GuV, Bilanz, Cashflow) öffnen"):
                t1, t2, t3 = st.tabs(["GuV", "Bilanz", "Cashflow"])
                with t1:
                    st.dataframe(financials_df, use_container_width=True)
                with t2:
                    st.dataframe(balance_sheet_df, use_container_width=True)
                with t3:
                    st.dataframe(cashflow_df, use_container_width=True)

        # ------------------------------------------
        # TAB 4: DIVIDENDE & PEER-GROUP
        # ------------------------------------------
        with tab_div_peers:
            st.subheader("💰 Dividenden-Kennzahlen")
            div_yield = (info.get('dividendYield') or 0) * 100
            div_rate = info.get('dividendRate') or 0
            payout_ratio = (info.get('payoutRatio') or 0) * 100
            div_rate_eur = div_rate * eur_rate

            d1, d2, d3 = st.columns(3)
            d1.metric("Dividendenrendite", f"{div_yield:.2f}%")
            d2.metric("Dividende / Aktie p.a.", f"{div_rate_eur:.2f} €", delta=f"{div_rate:.2f} {curr_symbol}" if currency_code != "EUR" else None, delta_color="off")
            d3.metric("Ausschüttungsquote", f"{payout_ratio:.1f}%")

            if not dividends_data.empty:
                div_df = dividends_data.tail(16).to_frame(name="Ausschüttung")
                div_df['EUR'] = div_df['Ausschüttung'] * eur_rate
                fig_div = go.Figure(go.Bar(x=div_df.index, y=div_df['EUR'], marker_color="#2ea043", name="Dividende (€)"))
                fig_div.update_layout(template="plotly_dark", height=260, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10), yaxis_title="€ / Aktie")
                st.plotly_chart(fig_div, use_container_width=True)
            else:
                st.info("Dieses Unternehmen schüttet aktuell keine Dividende aus.")

            st.markdown("---")
            st.subheader("⚔️ Branchen- & Peer-Vergleich")
            p_in_col, p_btn_col = st.columns([3, 1])
            with p_in_col:
                peer_input = st.text_input("Vergleichs-Ticker:", value=f"{ticker_symbol}, MSFT, GOOGL, NVDA", label_visibility="collapsed")
            with p_btn_col:
                run_peers = st.button("Vergleichen", use_container_width=True)

            if run_peers:
                peer_list = list(dict.fromkeys([p.strip().upper() for p in peer_input.split(",") if p.strip()]))
                with ThreadPoolExecutor(max_workers=6) as executor:
                    peer_raw = list(executor.map(load_quick_quote, peer_list))

                peer_data = []
                for item in peer_raw:
                    p_sym, p_inf = item["symbol"], item["info"]
                    if not p_inf:
                        continue
                    p_rate = get_eur_exchange_rate(p_inf.get('currency', 'USD'))
                    p_price = p_inf.get('currentPrice') or p_inf.get('regularMarketPrice') or 0
                    peer_data.append({
                        "Symbol": p_sym,
                        "Name": p_inf.get('shortName', p_sym),
                        "Kurs (EUR €)": f"{p_price * p_rate:.2f} €",
                        "KGV (Fwd)": round(p_inf.get('forwardPE', 0), 2) if p_inf.get('forwardPE') else "N/A",
                        "Nettomarge": f"{(p_inf.get('profitMargins') or 0)*100:.1f}%",
                        "ROE": f"{(p_inf.get('returnOnEquity') or 0)*100:.1f}%"
                    })
                st.dataframe(pd.DataFrame(peer_data), use_container_width=True, hide_index=True)

        # ------------------------------------------
        # TAB 5: NEWS & TERMINE
        # ------------------------------------------
        with tab_news:
            n_col1, n_col2 = st.columns([1, 1.5], gap="large")
            with n_col1:
                st.subheader("📅 Nächste Quartalszahlen")
                if calendar_data is not None and not (isinstance(calendar_data, pd.DataFrame) and calendar_data.empty):
                    try:
                        cal_dict = calendar_data if isinstance(calendar_data, dict) else calendar_data.to_dict()
                        e_date = cal_dict.get('Earnings Date', ['N/A'])[0] if isinstance(cal_dict.get('Earnings Date'), list) else cal_dict.get('Earnings Date', 'N/A')
                        eps_avg = cal_dict.get('Earnings Average', 'N/A')
                        rev_avg = cal_dict.get('Revenue Average', 'N/A')

                        st.metric("Termin (Earnings Date)", str(e_date))
                        st.metric("Erwarteter Gewinn / Aktie (EPS)", str(eps_avg))
                        if isinstance(rev_avg, (int, float)):
                            st.metric("Erwarteter Umsatz", f"{rev_avg / 1e9:.2f} Mrd. {curr_symbol}")
                    except Exception:
                        st.info("Keine detaillierten Termindaten verfügbar.")
                else:
                    st.info("Aktuell kein bevorstehender Termin hinterlegt.")

            with n_col2:
                st.subheader("📰 Aktuelle Nachrichten")
                if news_data:
                    for item in news_data[:6]:
                        c = item.get('content', item)
                        title = c.get('title', 'Titel')
                        url = c.get('canonicalUrl', {}).get('url', c.get('link', '#'))
                        provider = c.get('provider', {}).get('displayName', c.get('publisher', 'N/A'))
                        st.markdown(f"**[{title}]({url})**  \n<span style='color:#8b949e; font-size:12px;'>Quelle: {provider}</span>", unsafe_allow_html=True)
                        st.markdown("<hr style='margin: 8px 0; border-color: #21262d;'>", unsafe_allow_html=True)
                else:
                    st.info("Keine aktuellen Nachrichten verfügbar.")

    except Exception as e:
        st.error(f"Fehler beim Laden von {ticker_symbol}: {e}")

# ==========================================
# ANSICHT 2: AKTIEN-SCREENER (MIT 1-KLICK-ANALYSE)
# ==========================================
elif main_nav == "🔍 Aktien-Screener":
    st.markdown("## 🔍 Aktien-Screener & Einstiegs-Finder")
    st.caption("Filtere Märkte nach Fundamentaldaten, Volume-Supports und ATR-Einstiegszonen. Klicke eine Zeile an, um die Aktie direkt zu öffnen.")

    s_c1, s_c2, s_c3 = st.columns([1.2, 1.2, 1])
    with s_c1:
        selected_preset = st.selectbox("Markt / Liste:", list(SCREENER_LISTS.keys()))
        min_score = st.slider("Mindest-Score (0–5):", 0, 5, 2)
    with s_c2:
        signal_filter = st.multiselect(
            "Einstiegs-Signale filtern:",
            [
                "🔥 Volumen-Ausbruch (> 1.5x Ø Vol)",
                "📈 20-Tage-Hoch Durchbruch",
                "📉 RSI Überverkauft (< 35)",
                "🎯 Nahe 200-SMA Support (±1 ATR)",
                "📊 Nahe Volume POC (±1 ATR)",
                "⚓ Nahe Anchored VWAP (±1 ATR)"
            ],
            default=[]
        )
        max_pe = st.number_input("Maximales Forward KGV:", value=45.0, step=5.0)
    with s_c3:
        custom_symbols_input = st.text_area("Symbole (anpassbar):", value=", ".join(SCREENER_LISTS[selected_preset]), height=115)

    if st.button("🚀 Markt jetzt scannen", use_container_width=True):
        symbols_to_scan = list(dict.fromkeys([s.strip().upper() for s in custom_symbols_input.split(",") if s.strip()]))
        results = []

        with st.spinner(f"Analysiere {len(symbols_to_scan)} Aktien..."):
            with ThreadPoolExecutor(max_workers=8) as executor:
                scanned_items = list(executor.map(load_quick_quote, symbols_to_scan))

        for item in scanned_items:
            sym, inf, df_h = item["symbol"], item["info"], item["hist"]
            if df_h.empty or len(df_h) < 50:
                continue

            f_pe = inf.get('forwardPE') or 999
            margin = (inf.get('profitMargins') or 0) * 100
            roe_sc = (inf.get('returnOnEquity') or 0) * 100
            price = inf.get('currentPrice') or inf.get('regularMarketPrice') or df_h['Close'].iloc[-1]
            s_rate = get_eur_exchange_rate(inf.get('currency', 'USD'))

            ez = analyze_entry_zones(df_h, price)
            if not ez["valid"]:
                continue

            last_c = df_h['Close'].iloc[-1]
            last_s200, last_r, atr_val = ez["last_sma200"], ez["last_rsi"], ez["atr_14"]
            poc_val, avwap_val = ez["poc_price"], ez["last_avwap"]

            avg_vol = df_h['Volume'].rolling(20).mean().iloc[-1]
            last_vol = df_h['Volume'].iloc[-1]
            high_20d = df_h['High'].iloc[-21:-1].max() if len(df_h) > 21 else df_h['High'].max()

            c_score = sum([
                last_c > last_s200,
                last_r < 35,
                0 < f_pe < 25,
                margin > 12,
                roe_sc > 12
            ])

            today_signals = []
            if avg_vol > 0 and (last_vol / avg_vol) >= 1.5:
                today_signals.append("🔥 Vol-Spike")
            if last_c >= high_20d:
                today_signals.append("📈 20D-Breakout")
            if last_r <= 35:
                today_signals.append("📉 RSI Oversold")
            if abs(last_c - last_s200) <= atr_val:
                today_signals.append("🎯 200-SMA Support")
            if abs(last_c - poc_val) <= atr_val:
                today_signals.append("📊 Volume POC")
            if abs(last_c - avwap_val) <= atr_val:
                today_signals.append("⚓ Anchored VWAP")

            filter_map = {
                "🔥 Volumen-Ausbruch (> 1.5x Ø Vol)": "🔥 Vol-Spike",
                "📈 20-Tage-Hoch Durchbruch": "📈 20D-Breakout",
                "📉 RSI Überverkauft (< 35)": "📉 RSI Oversold",
                "🎯 Nahe 200-SMA Support (±1 ATR)": "🎯 200-SMA Support",
                "📊 Nahe Volume POC (±1 ATR)": "📊 Volume POC",
                "⚓ Nahe Anchored VWAP (±1 ATR)": "⚓ Anchored VWAP"
            }
            if any(tag not in today_signals for f_label, tag in filter_map.items() if f_label in signal_filter):
                continue

            if c_score >= min_score and f_pe <= max_pe:
                results.append({
                    "Symbol": sym,
                    "Name": inf.get('shortName', sym),
                    "Signale": ", ".join(today_signals) if today_signals else "➖ Neutral",
                    "Konfluenz": f"{ez['confluence_count']} Akt.",
                    "Score": f"{c_score} / 5",
                    "Kurs (€)": f"{price * s_rate:.2f} €",
                    "Volume POC (€)": f"{poc_val * s_rate:.2f} €",
                    "Abstand 200-SMA": f"{ez['atr_dist_sma200']:+.1f}x ATR",
                    "Fwd KGV": round(f_pe, 1) if f_pe != 999 else "N/A",
                    "RSI": round(last_r, 1)
                })

        st.session_state.screener_df = pd.DataFrame(results)

    if "screener_df" in st.session_state:
        df_res = st.session_state.screener_df
        if not df_res.empty:
            st.success(f"**{len(df_res)} Treffer gefunden** – Zeile anklicken, um direkt zur Detail-Analyse zu springen:")
            event = st.dataframe(
                df_res,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            if event.selection.rows:
                chosen_sym = df_res.iloc[event.selection.rows[0]]["Symbol"]
                open_ticker_analysis(chosen_sym)
                st.rerun()
        else:
            st.warning("Keine Treffer für diese Filterkombination.")

# ==========================================
# ANSICHT 3: WATCHLIST (MIT 1-KLICK-ANALYSE)
# ==========================================
elif main_nav == "⭐ Watchlist":
    st.markdown("## ⭐ Watchlist")
    st.caption("Klicke eine Aktie an, um direkt die Analyse zu öffnen.")

    if st.session_state.watchlist:
        with st.spinner("Aktualisiere Watchlist..."):
            with ThreadPoolExecutor(max_workers=8) as executor:
                wl_raw = list(executor.map(load_quick_quote, st.session_state.watchlist))

        wl_data = []
        for item in wl_raw:
            w_sym, w_inf = item["symbol"], item["info"]
            w_curr = w_inf.get('currency', 'USD')
            w_rate = get_eur_exchange_rate(w_curr)
            price_val = w_inf.get('currentPrice') or w_inf.get('regularMarketPrice') or 0
            prev_close = w_inf.get('previousClose') or price_val

            if price_val and prev_close:
                change_abs = price_val - prev_close
                change_pct = (change_abs / prev_close) * 100
                price_eur = price_val * w_rate
                icon = "🟢" if change_pct >= 0 else "🔴"
                change_str = f"{icon} {change_abs * w_rate:+.2f} € ({change_pct:+.2f}%)"
            else:
                price_eur, change_str = 0, "N/A"

            wl_data.append({
                "Symbol": w_sym,
                "Name": w_inf.get('shortName', w_sym),
                "Kurs (€)": f"{price_eur:.2f} €" if price_eur else "N/A",
                "Heute": change_str,
                "Kurs (Orig.)": f"{price_val:.2f} {w_curr}" if price_val else "N/A",
                "Fwd KGV": round(w_inf.get('forwardPE', 0), 1) if w_inf.get('forwardPE') else "N/A",
                "Branche": w_inf.get('industry', 'N/A')
            })

        df_wl = pd.DataFrame(wl_data)
        wl_event = st.dataframe(
            df_wl,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        if wl_event.selection.rows:
            chosen_sym = df_wl.iloc[wl_event.selection.rows[0]]["Symbol"]
            open_ticker_analysis(chosen_sym)
            st.rerun()

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        c_rm1, c_rm2, c_rm3 = st.columns([2, 1, 1])
        with c_rm1:
            remove_sym = st.selectbox("Aktie entfernen:", st.session_state.watchlist, label_visibility="collapsed")
        with c_rm2:
            if st.button("❌ Entfernen", use_container_width=True):
                st.session_state.watchlist.remove(remove_sym)
                st.rerun()
        with c_rm3:
            csv_data = pd.DataFrame({"Symbol": st.session_state.watchlist}).to_csv(index=False).encode('utf-8')
            st.download_button("💾 CSV Export", data=csv_data, file_name="watchlist.csv", mime="text/csv", use_container_width=True)
    else:
        st.info("Deine Watchlist ist aktuell leer. Nutze in der Analyse oben rechts den Button **⭐ Merken**.")

# ==========================================
# ANSICHT 4: MARKT & STIMMUNG
# ==========================================
elif main_nav == "🌐 Markt & Stimmung":
    st.markdown("## 🌐 Globale Marktstimmung & Sektor-Rotation")
    st.caption("Makro-Überblick über Indizes, Volatilität (VIX) und Branchen-Trends.")

    with st.spinner("Lade Marktdaten..."):
        try:
            sp500, vix, dax, sector_data = load_market_overview()

            last_sp500 = sp500['Close'].iloc[-1]
            sp500_sma200 = ta.trend.sma_indicator(sp500['Close'], window=200).iloc[-1]
            vix_level = vix['Close'].iloc[-1] if not vix.empty else 20.0
            sp500_rsi = ta.momentum.rsi(sp500['Close'], window=14).iloc[-1]

            vix_score = max(0, min(100, (35 - vix_level) * 4))
            mom_diff = ((last_sp500 - sp500_sma200) / sp500_sma200) * 100
            mom_score = max(0, min(100, 50 + (mom_diff * 5)))
            fg_index = int((vix_score * 0.4) + (sp500_rsi * 0.3) + (mom_score * 0.3))

            if fg_index <= 25:
                fg_status = "😱 Extreme Angst"
            elif fg_index <= 45:
                fg_status = "😨 Angst"
            elif fg_index <= 55:
                fg_status = "😐 Neutral"
            elif fg_index <= 75:
                fg_status = "🤑 Gier"
            else:
                fg_status = "🔥 Extreme Gier"

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Fear & Greed Index", f"{fg_index} / 100", delta=fg_status)
            m2.metric("S&P 500 Trend", f"{last_sp500:,.0f} Pkt.", delta="🟢 Bullenmarkt" if last_sp500 > sp500_sma200 else "🔴 Bärenmarkt")
            m3.metric("VIX Volatilität", f"{vix_level:.1f}", delta="🟢 Entspannt" if vix_level < 15 else ("🟡 Moderat" if vix_level < 25 else "🔴 Panik"))

            last_dax = dax['Close'].iloc[-1]
            dax_sma200 = ta.trend.sma_indicator(dax['Close'], window=200).iloc[-1]
            m4.metric("DAX Index", f"{last_dax:,.0f} Pkt.", delta="🟢 Aufwärtstrend" if last_dax > dax_sma200 else "🔴 Abwärtstrend")

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            if fg_index <= 25:
                st.info("**Antizyklische Kaufphase (Extreme Angst):** Der Markt ist stark überverkauft – historisch oft attraktive Einstiege für Qualitätsaktien.")
            elif fg_index >= 75:
                st.warning("**Überhitzte Marktphase (Extreme Gier):** Teilgewinne absichern, Stop-Loss nachziehen und keine Ausbrüche blind verfolgen.")
            else:
                st.success("**Ausgeglichenes Marktumfeld:** Fokus auf Einzelwert-Auswahl (Stock-Picking) an starken Volume-Supports.")

            if sector_data:
                st.subheader("📊 Sektor-Rotation (Performance 1 Monat)")
                df_sectors = pd.DataFrame(sector_data).sort_values(by="Performance (%)", ascending=True)
                fig_sec = go.Figure(go.Bar(
                    x=df_sectors['Performance (%)'],
                    y=df_sectors['Sektor'],
                    orientation='h',
                    marker_color=['#2ea043' if val >= 0 else '#f85149' for val in df_sectors['Performance (%)']]
                ))
                fig_sec.update_layout(template="plotly_dark", height=320, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title="Performance in %", margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_sec, use_container_width=True)

        except Exception as e:
            st.error(f"Fehler bei der Marktanalyse: {e}")
