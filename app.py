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
# CUSTOM CSS FOR MINIMALISTIC & CLEAN UI
# ==========================================
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #21262d;
    }
    div[data-testid="stMetric"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: none;
        transition: border-color 0.15s ease;
        min-height: 110px !important;
        height: 110px !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #8b949e;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        min-height: 110px !important;
        height: 110px !important;
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 12px !important;
    }
    .banner-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px 16px;
        min-height: 110px !important;
        height: 110px !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .banner-card h4 {
        margin: 0 0 4px 0 !important;
        font-size: 13px !important;
        color: #8b949e !important;
        font-weight: 500 !important;
    }
    .banner-card h3 {
        margin: 0 !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }
    .banner-card-success { border-left: 3px solid #2ea043; }
    .banner-card-warning { border-left: 3px solid #d29922; }
    .banner-card-danger { border-left: 3px solid #f85149; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid #21262d;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        color: #8b949e;
        padding: 8px 12px;
        font-size: 14px;
        font-weight: 400;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        color: #f0f6fc !important;
        border-bottom-color: #f0f6fc !important;
        font-weight: 600;
    }
    .stButton > button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        font-weight: 500;
        font-size: 13px;
        padding: 6px 14px;
        transition: background-color 0.15s ease, border-color 0.15s ease;
    }
    .stButton > button:hover {
        background-color: #30363d;
        border-color: #8b949e;
        color: #ffffff;
        box-shadow: none;
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

if 'risk_preset' not in st.session_state:
    st.session_state.risk_preset = {"ticker": None, "entry": None, "sl": None, "label": "Aktueller Kurs"}

# ==========================================
# CACHING & DATEN-LAYER
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_eur_exchange_rate(currency: str) -> float:
    """Liefert den Umrechnungsfaktor von der Zielwährung in EUR."""
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
    """Schnellabruf für Watchlist, Peers und Screener."""
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
    """
    Berechnet präzise Multi-Faktor-Einstiegszonen:
    - 14-Tage ATR (volatilitätsangepasste Bänder & Stop-Loss)
    - 50-SMA & 200-SMA ATR-Kaufzonen
    - Fibonacci-Retracements (38.2%, 50.0%, Golden Pocket 61.8% - 65.0%)
    - Volume Profile & Point of Control (POC)
    - Anchored VWAP ab dem 52-Wochen-Tief
    - Confluence-Score (Anzahl überlappender Unterstützungsfaktoren)
    """
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

    # 1. ATR-basierte Trend-Kaufzonen
    sma50_low = last_sma50 - (0.5 * atr_14)
    sma50_high = last_sma50 + (0.5 * atr_14)
    sma200_low = last_sma200 - (0.5 * atr_14)
    sma200_high = last_sma200 + (0.5 * atr_14)

    # 2. Fibonacci Retracements (52W Tief -> 52W Hoch)
    fib_range = max(high_52 - low_52, 0.01)
    fib_382 = high_52 - (0.382 * fib_range)
    fib_500 = high_52 - (0.500 * fib_range)
    fib_618 = high_52 - (0.618 * fib_range)
    fib_650 = high_52 - (0.650 * fib_range)

    # 3. Volume Profile (24 Preis-Buckets) & Point of Control (POC)
    bins = np.linspace(low_52, high_52, 25)
    binned = pd.cut(work['Close'], bins=bins, include_lowest=True)
    vol_by_bin = work.groupby(binned, observed=False)['Volume'].sum()
    bin_mids = [iv.mid for iv in vol_by_bin.index]
    bin_vols = vol_by_bin.values.tolist()

    poc_idx = int(np.argmax(bin_vols)) if len(bin_vols) > 0 else 0
    poc_price = float(bin_mids[poc_idx]) if len(bin_mids) > 0 else last_sma200

    # 4. Anchored VWAP ab dem 52-Wochen-Tief
    anchored_df = work.loc[low_52_idx:].copy()
    typical_price = (anchored_df['High'] + anchored_df['Low'] + anchored_df['Close']) / 3.0
    cum_vol = anchored_df['Volume'].cumsum().replace(0, np.nan)
    anchored_df['AVWAP'] = (typical_price * anchored_df['Volume']).cumsum() / cum_vol
    last_avwap = float(anchored_df['AVWAP'].iloc[-1]) if pd.notna(anchored_df['AVWAP'].iloc[-1]) else last_sma200

    # 5. Technischer Stop-Loss Vorschlag (2x ATR unter 200-SMA-Kaufzone)
    suggested_sl_200 = max(0.01, sma200_low - (2.0 * atr_14))
    suggested_sl_curr = max(0.01, current_price - (2.0 * atr_14))

    # 6. Confluence-Check (Überlappende Kaufsignale am aktuellen Kurs)
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

    # ATR-normalisierter Abstand zur 200-SMA Hauptzone
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
        "low_52_date": low_52_idx,
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
    """Berechnet die verbleibenden Tage bis zum nächsten Earnings-Termin."""
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
    """Vollständiger 9-Punkte Piotroski F-Score."""
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
# SEITENLEISTE: NAVIGATION & FAVORITEN
# ==========================================
st.sidebar.markdown("## 🤑 GEILEPROFITE")

main_nav = st.sidebar.radio(
    "Navigation",
    ["📊 Aktien-Analyse", "⭐ Watchlist", "🔍 Aktien-Screener", "🌐 Markt & Zukunft"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
ticker_symbol = st.session_state.active_ticker

if st.sidebar.button(f"➕ {ticker_symbol} speichern", use_container_width=True):
    if ticker_symbol not in st.session_state.watchlist:
        st.session_state.watchlist.append(ticker_symbol)
        st.sidebar.success(f"{ticker_symbol} gespeichert!")
        st.rerun()

if st.session_state.watchlist:
    st.sidebar.markdown("#### ⭐ Favoriten")
    with ThreadPoolExecutor(max_workers=5) as executor:
        fav_results = list(executor.map(load_quick_quote, st.session_state.watchlist[:5]))

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
            label_str = f"{w_sym} | {price_eur:.2f} € ({icon} {change_pct:+.1f}%)"
        else:
            label_str = f"{w_sym}"

        if st.sidebar.button(label_str, key=f"fav_btn_{w_sym}", use_container_width=True):
            st.session_state.active_ticker = w_sym
            st.rerun()

# ==========================================
# FENSTER 1: AKTIEN-ANALYSE
# ==========================================
if main_nav == "📊 Aktien-Analyse":
    col_search1, col_search2 = st.columns([3, 1])

    with col_search1:
        search_input = st.text_input(
            "Suchbegriff oder Ticker-Symbol:",
            placeholder="z. B. Apple, NVDA, SAP.DE, TSLA...",
            label_visibility="collapsed"
        )
    with col_search2:
        btn_search = st.button("🔍 Suchen", use_container_width=True)

    if search_input:
        search_results = search_ticker(search_input)
        if search_results:
            selected_option = st.selectbox(
                "Suchergebnisse (wählen zum Analysieren):",
                options=[opt[0] for opt in search_results],
                key="select_search_result"
            )
            for label, sym in search_results:
                if label == selected_option and st.session_state.active_ticker != sym:
                    st.session_state.active_ticker = sym
                    st.rerun()
        elif btn_search:
            direct_sym = search_input.strip().upper()
            if direct_sym != st.session_state.active_ticker:
                st.session_state.active_ticker = direct_sym
                st.rerun()

    ticker_symbol = st.session_state.active_ticker
    st.markdown("---")

    if ticker_symbol:
        try:
            with st.spinner(f"Lade Live-Daten für {ticker_symbol}..."):
                info, df_daily, cashflow_df, financials_df, balance_sheet_df, news_data, calendar_data, dividends_data = load_stock_data(ticker_symbol)

            if not info or (not info.get('regularMarketPrice') and not info.get('currentPrice') and df_daily.empty):
                st.error(f"Keine gültigen Marktdaten für **{ticker_symbol}** gefunden. Bitte überprüfe das Ticker-Symbol (z. B. `SAP.DE` für Xetra).")
                st.stop()

            company_name = info.get('longName', ticker_symbol)
            raw_currency = info.get('currency', 'USD')
            currency_code = raw_currency.upper()
            curr_symbol = "$" if currency_code == "USD" else ("€" if currency_code == "EUR" else currency_code)
            eur_rate = get_eur_exchange_rate(raw_currency)

            st.markdown(f"## {company_name} <span style='color:#8b949e; font-size: 20px;'>({info.get('symbol', ticker_symbol)})</span>", unsafe_allow_html=True)
            st.caption(f"**Branche:** {info.get('industry', 'N/A')} | **Sektor:** {info.get('sector', 'N/A')} | **Währung:** {raw_currency} (Faktor zu EUR: {eur_rate:.4f})")

            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or (df_daily['Close'].iloc[-1] if not df_daily.empty else 0)
            kgv = info.get('forwardPE', 'N/A')
            marge = info.get('profitMargins', 0) * 100 if info.get('profitMargins') is not None else 'N/A'
            beta = info.get('beta', 'N/A')

            # Multi-Faktor Einstiegszonen berechnen
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

            # DCF Basisdaten
            raw_fcf = _get_row_val(cashflow_df, ['Free Cash Flow'], 0, 0)
            free_cash_flow_m = raw_fcf / 1e6 if raw_fcf else 0.0
            shares_outstanding_m = (info.get('sharesOutstanding') or 0) / 1e6
            total_debt_m = (info.get('totalDebt') or 0) / 1e6
            total_cash_m = (info.get('totalCash') or 0) / 1e6
            net_debt_m = total_debt_m - total_cash_m

            dcf_fair_value = calculate_dcf(free_cash_flow_m, net_debt_m, shares_outstanding_m)
            dcf_margin = ((dcf_fair_value - current_price) / current_price) * 100 if (current_price and dcf_fair_value > 0) else 0

            piotroski_score, piotroski_details = calculate_piotroski_score(financials_df, balance_sheet_df, cashflow_df)

            # Gesamt-Score (0-6)
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

            # EXECUTIVE BANNER
            st.markdown("<br>", unsafe_allow_html=True)
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)

            with b_col1:
                if score >= 5:
                    st.markdown("<div class='banner-card banner-card-success'><h4>🔥 Gesamt-Urteil</h4><h3 style='color:#10b981;'>STARKES KAUFSIGNAL</h3></div>", unsafe_allow_html=True)
                elif score >= 3:
                    st.markdown("<div class='banner-card banner-card-warning'><h4>⚠️ Gesamt-Urteil</h4><h3 style='color:#f59e0b;'>HALTEN / WATCHLIST</h3></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='banner-card banner-card-danger'><h4>⛔ Gesamt-Urteil</h4><h3 style='color:#ef4444;'>MEIDEN / VORSICHT</h3></div>", unsafe_allow_html=True)

            with b_col2:
                st.metric("Gesamt-Score", f"{score} / {max_score} Pkt.", delta=f"Piotroski: {piotroski_score}/9")

            with b_col3:
                if dcf_fair_value > 0:
                    dcf_eur = dcf_fair_value * eur_rate
                    delta_str = f"{dcf_margin:+.1f}% vs. Kurs"
                    if currency_code != "EUR":
                        st.metric("DCF Fairer Wert", f"{dcf_fair_value:.2f} {curr_symbol}", delta=f"~ {dcf_eur:.2f} € | {delta_str}")
                    else:
                        st.metric("DCF Fairer Wert", f"{dcf_fair_value:.2f} €", delta=delta_str)
                else:
                    st.metric("DCF Fairer Wert", "N/A", delta="Negativer/Fehlender FCF", delta_color="off")

            with b_col4:
                pdf_bytes = generate_pdf_report(
                    ticker_symbol, company_name, current_price, dcf_fair_value,
                    score, piotroski_score, reasons, curr_symbol, eur_rate, entry_data
                )
                with st.container(border=True):
                    st.markdown("<h4 style='margin:0 0 8px 0; font-size:14px; color:#8b949e;'>📄 Export</h4>", unsafe_allow_html=True)
                    st.download_button("PDF Exportieren", data=pdf_bytes, file_name=f"{ticker_symbol}_Analyse.pdf", mime="application/pdf", use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            price_eur = current_price * eur_rate
            if currency_code != "EUR":
                col1.metric("Aktueller Kurs", f"{current_price:.2f} {curr_symbol}", delta=f"~ {price_eur:.2f} €")
            else:
                col1.metric("Aktueller Kurs", f"{current_price:.2f} €")

            col2.metric("Forward KGV", f"{kgv:.2f}" if isinstance(kgv, (int, float)) else str(kgv))
            col3.metric("Nettomarge", f"{marge:.2f}%" if isinstance(marge, (int, float)) else str(marge))
            col4.metric("Beta (S&P 500)", f"{beta:.2f}" if isinstance(beta, (int, float)) else str(beta))

            st.markdown("<br>", unsafe_allow_html=True)

            # UNTER-TABS
            tab_chart, tab_entry, tab_risk, tab_analysts, tab_dividends, tab_peers, tab_news, tab_signals, tab_dcf, tab_finances = st.tabs([
                "📈 Chart & Indikatoren",
                "🎯 Einstiegszonen",
                "🛡️ Positionsrechner",
                "🎯 Analysten-Ratings",
                "💰 Dividenden",
                "⚔️ Peer-Group",
                "📰 News & Termine",
                "🚦 Lage-Analyse",
                "🧮 DCF-Modell",
                "📑 Finanzen"
            ])

            # ------------------------------------------
            # TAB 1: CHART & INDIKATOREN
            # ------------------------------------------
            with tab_chart:
                st.subheader("Kursverlauf & Indikatoren")
                col_tf1, col_tf2, col_tf3 = st.columns([1, 1, 1])
                with col_tf1:
                    timeframe = st.selectbox(
                        "Zeitraum:",
                        ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
                        index=5
                    )
                with col_tf2:
                    if timeframe == "1d":
                        interval_options = ["1m", "2m", "5m", "15m", "30m", "60m"]
                        default_idx = 2
                    elif timeframe == "5d":
                        interval_options = ["5m", "15m", "30m", "60m", "1d"]
                        default_idx = 1
                    else:
                        interval_options = ["1d", "1wk", "1mo"]
                        default_idx = 0
                    interval = st.selectbox("Intervall (Auflösung):", interval_options, index=default_idx)
                with col_tf3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    show_bb = st.checkbox("Bollinger Bänder & SMA", value=True)

                hist = load_chart_history(ticker_symbol, timeframe, interval)

                if not hist.empty:
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.72, 0.28])

                    fig.add_trace(go.Candlestick(
                        x=hist.index,
                        open=hist['Open'],
                        high=hist['High'],
                        low=hist['Low'],
                        close=hist['Close'],
                        name=f"Kurs ({curr_symbol})"
                    ), row=1, col=1)

                    if show_bb and len(hist) >= 20:
                        bb = ta.volatility.BollingerBands(close=hist['Close'], window=20, window_dev=2)
                        fig.add_trace(go.Scatter(x=hist.index, y=bb.bollinger_hband(), line=dict(color='rgba(255, 255, 255, 0.3)', width=1), name="BB Oben"), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=bb.bollinger_lband(), line=dict(color='rgba(255, 255, 255, 0.3)', width=1), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)', name="BB Unten"), row=1, col=1)
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
                        xaxis_rangeslider_visible=False,
                        template="plotly_dark",
                        height=600,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=10, r=10, t=20, b=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Keine Daten für dieses Zeitraum-/Intervall-Paar verfügbar.")

            # ------------------------------------------
            # TAB 2: MULTI-FAKTOR EINSTIEGSZONEN
            # ------------------------------------------
            with tab_entry:
                if entry_data["valid"]:
                    st.subheader("🎯 Multi-Faktor Einstiegszonen & Volume Profile")

                    # Earnings-Sperrfilter Warnung
                    days_to_earn = get_days_to_earnings(calendar_data)
                    if days_to_earn is not None and days_to_earn <= 7:
                        st.error(f"⚠️ **Earnings-Warnung:** In **{days_to_earn} Tag(en)** stehen Quartalszahlen an! Technische Unterstützungen können durch Kurs-Gaps übersprungen werden.")

                    atr_14 = entry_data["atr_14"]
                    poc_price = entry_data["poc_price"]
                    last_avwap = entry_data["last_avwap"]
                    sma50_low, sma50_high = entry_data["sma50_low"], entry_data["sma50_high"]
                    sma200_low, sma200_high = entry_data["sma200_low"], entry_data["sma200_high"]
                    fib_382, fib_500 = entry_data["fib_382"], entry_data["fib_500"]
                    fib_618, fib_650 = entry_data["fib_618"], entry_data["fib_650"]
                    suggested_sl_200 = entry_data["suggested_sl_200"]
                    confluence_hits = entry_data["confluence_hits"]

                    # Kennzahlen-Leiste
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("14-Tage ATR (Volatilität)", f"{atr_14:.2f} {curr_symbol}", delta=f"{(atr_14/current_price)*100:.1f}% Ø Tagesspanne", delta_color="off")
                    m2.metric("Volume POC (Haupt-Support)", f"{poc_price:.2f} {curr_symbol}", delta=f"~ {poc_price*eur_rate:.2f} €")
                    m3.metric("Anchored VWAP (52W-Tief)", f"{last_avwap:.2f} {curr_symbol}", delta=f"~ {last_avwap*eur_rate:.2f} €")
                    m4.metric("ATR Stop-Loss (200-SMA)", f"{suggested_sl_200:.2f} {curr_symbol}", delta=f"~ {suggested_sl_200*eur_rate:.2f} €")

                    st.markdown("<br>", unsafe_allow_html=True)

                    ez_col1, ez_col2 = st.columns([1, 1.5])

                    with ez_col1:
                        if len(confluence_hits) >= 2:
                            st.success(f"**🔥 Starke Einstiegs-Konfluenz ({len(confluence_hits)} Faktoren aktiv):**\n- " + "\n- ".join(confluence_hits))
                        elif len(confluence_hits) == 1:
                            st.info(f"**⚡ Moderater Support aktiv:** {confluence_hits[0]}")
                        else:
                            st.warning(f"**⏳ Kein direkter Support-Test** – Kurs notiert {entry_data['atr_dist_sma200']:+.1f}x ATR vom 200-SMA entfernt.")

                        st.markdown(f"""
                        **Gestaffelter Tranchen-Kaufplan:**
                        * **Tranche 1 (Trend-Rücksetzer / 50-SMA ± 0.5 ATR):**  
                          `{sma50_low:.2f} – {sma50_high:.2f} {curr_symbol}` *(~ {sma50_low*eur_rate:.2f} – {sma50_high*eur_rate:.2f} €)*
                        * **Tranche 2 (Fibonacci Golden Pocket 61.8–65%):**  
                          `{fib_650:.2f} – {fib_618:.2f} {curr_symbol}` *(~ {fib_650*eur_rate:.2f} – {fib_618*eur_rate:.2f} €)*
                        * **Tranche 3 (Haupt-Kaufzone / 200-SMA ± 0.5 ATR):**  
                          `{sma200_low:.2f} – {sma200_high:.2f} {curr_symbol}` *(~ {sma200_low*eur_rate:.2f} – {sma200_high*eur_rate:.2f} €)*
                        * **Weitere Marken:** Fib 38.2%: `{fib_382:.2f}` | Fib 50%: `{fib_500:.2f}` | 52W-Tief: `{entry_data['low_52']:.2f}`
                        """)

                        # Direkt-Übergabe in den Positionsrechner
                        st.markdown("**🔗 Mit Positionsrechner verknüpfen:**")
                        btn_p1, btn_p2 = st.columns(2)
                        with btn_p1:
                            if st.button("📌 Aktueller Kurs + ATR-SL", use_container_width=True):
                                st.session_state.risk_preset = {
                                    "ticker": ticker_symbol,
                                    "entry": float(current_price),
                                    "sl": float(entry_data["suggested_sl_curr"]),
                                    "label": "Aktueller Kurs (2x ATR Stop)"
                                }
                                st.toast("Werte in den Tab 'Positionsrechner' übernommen!")
                        with btn_p2:
                            if st.button("🎯 200-SMA Limit + ATR-SL", use_container_width=True):
                                st.session_state.risk_preset = {
                                    "ticker": ticker_symbol,
                                    "entry": float(last_sma200),
                                    "sl": float(suggested_sl_200),
                                    "label": "200-SMA Limit-Order (2x ATR Stop)"
                                }
                                st.toast("200-SMA Limit-Order in den Tab 'Positionsrechner' übernommen!")

                    with ez_col2:
                        # Chart mit seitlichem Volume Profile Histogramm
                        fig_entry = make_subplots(
                            rows=1, cols=2,
                            shared_yaxes=True,
                            column_widths=[0.82, 0.18],
                            horizontal_spacing=0.01
                        )

                        df_e = entry_data["df"]
                        avwap_s = entry_data["avwap_series"]

                        # Kurs & Gleitende Durchschnitte
                        fig_entry.add_trace(go.Scatter(x=df_e.index, y=df_e['Close'], mode='lines', name='Kurs', line=dict(color='#e6edf3', width=1.8)), row=1, col=1)
                        fig_entry.add_trace(go.Scatter(x=df_e.index, y=df_e['SMA_50'], mode='lines', name='50-SMA', line=dict(color='#58a6ff', width=1.2)), row=1, col=1)
                        if entry_data["has_200"]:
                            fig_entry.add_trace(go.Scatter(x=df_e.index, y=df_e['SMA_200'], mode='lines', name='200-SMA', line=dict(dash='dash', color='#f59e0b', width=1.5)), row=1, col=1)

                        # Anchored VWAP ab 52W-Tief
                        fig_entry.add_trace(go.Scatter(x=avwap_s.index, y=avwap_s, mode='lines', name='Anchored VWAP', line=dict(color='#39d353', width=1.4, dash='dot')), row=1, col=1)

                        # Horizontale Zonen (200-SMA ATR & Fib Golden Pocket)
                        fig_entry.add_hrect(y0=sma200_low, y1=sma200_high, fillcolor="#2ea043", opacity=0.18, line_width=0, annotation_text="200-SMA ATR Zone", annotation_position="bottom left", row=1, col=1)
                        fig_entry.add_hrect(y0=fib_650, y1=fib_618, fillcolor="#a371f7", opacity=0.15, line_width=0, annotation_text="Fib Golden Pocket", annotation_position="top left", row=1, col=1)
                        fig_entry.add_hline(y=poc_price, line_dash="dot", line_color="#3fb950", annotation_text=f"POC ({poc_price:.1f})", row=1, col=1)

                        # Seitliches Volume Profile Histogramm
                        vp_colors = ['#3fb950' if abs(m - poc_price) < 1e-6 else 'rgba(139, 148, 158, 0.35)' for m in entry_data["vp_mids"]]
                        fig_entry.add_trace(go.Bar(
                            x=entry_data["vp_vols"],
                            y=entry_data["vp_mids"],
                            orientation='h',
                            name='Volume Profile',
                            marker_color=vp_colors,
                            showlegend=False
                        ), row=1, col=2)

                        fig_entry.update_layout(
                            template="plotly_dark",
                            height=460,
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            margin=dict(l=10, r=10, t=25, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
                        )
                        fig_entry.update_xaxes(showticklabels=False, showgrid=False, row=1, col=2)
                        st.plotly_chart(fig_entry, use_container_width=True)
                else:
                    st.info("Für die Berechnung der Einstiegszonen werden mindestens 50 Handelstage benötigt.")

            # ------------------------------------------
            # TAB 3: POSITIONSRECHNER (VERKNÜPFT MIT ATR)
            # ------------------------------------------
            with tab_risk:
                st.subheader("🛡️ Risk & Positionsgrößen-Rechner")

                preset = st.session_state.risk_preset
                use_preset = preset.get("ticker") == ticker_symbol and preset.get("entry") is not None

                default_entry = preset["entry"] if use_preset else float(current_price)
                default_sl = preset["sl"] if use_preset else (float(entry_data["suggested_sl_curr"]) if entry_data["valid"] else max(0.01, float(current_price * 0.95)))

                if use_preset:
                    st.info(f"Aktives Szenario aus Einstiegszonen: **{preset['label']}** (Einstieg: `{default_entry:.2f} {curr_symbol}`, ATR Stop-Loss: `{default_sl:.2f} {curr_symbol}`)")

                p_col1, p_col2 = st.columns([1, 1])
                with p_col1:
                    account_size_eur = st.number_input("Gesamtes Depotkapital (€):", value=10000.0, step=1000.0, min_value=100.0)
                    risk_pct = st.slider("Maximales Risiko pro Trade (%):", 0.5, 5.0, 1.0, 0.5) / 100
                    entry_price_curr = st.number_input(f"Geplanter Einstiegskurs ({curr_symbol}):", value=max(0.01, default_entry), step=1.0, min_value=0.01, key=f"entry_in_{ticker_symbol}_{default_entry:.2f}")
                    stop_loss_curr = st.number_input(f"Geplanter Stop-Loss Preis ({curr_symbol}):", value=max(0.01, default_sl), step=1.0, min_value=0.01, key=f"sl_in_{ticker_symbol}_{default_sl:.2f}")

                risk_amount_eur = account_size_eur * risk_pct
                risk_per_share_curr = entry_price_curr - stop_loss_curr
                risk_per_share_eur = risk_per_share_curr * eur_rate

                with p_col2:
                    if risk_per_share_curr > 0 and risk_per_share_eur > 0:
                        position_shares = int(risk_amount_eur / risk_per_share_eur)
                        position_value_curr = position_shares * entry_price_curr
                        position_value_eur = position_value_curr * eur_rate
                        stop_dist_pct = (risk_per_share_curr / entry_price_curr) * 100

                        st.success(f"**Empfohlene Kaufmenge:** {position_shares} Aktien")
                        st.metric("Positionsvolumen", f"{position_value_eur:,.2f} €", delta=f"{position_value_curr:,.2f} {curr_symbol}")
                        st.metric("Maximaler Verlust bei Stop-Loss", f"{risk_amount_eur:,.2f} €", delta=f"Stop-Abstand: -{stop_dist_pct:.1f}%", delta_color="off")
                    else:
                        st.error("Der Stop-Loss muss unter dem geplanten Einstiegskurs liegen!")

            # ------------------------------------------
            # TAB 4: ANALYSTEN-RATINGS
            # ------------------------------------------
            with tab_analysts:
                t_low = info.get('targetLowPrice')
                t_mean = info.get('targetMeanPrice')
                t_high = info.get('targetHighPrice')
                rec = (info.get('recommendationKey') or 'N/A').upper()
                num_analysts = info.get('numberOfAnalystOpinions', 'N/A')

                a_col1, a_col2, a_col3, a_col4 = st.columns(4)
                a_col1.metric("Konsens", rec, delta=f"{num_analysts} Analysten" if num_analysts != 'N/A' else None)
                a_col2.metric("Ziel Tief", f"{t_low:.2f} {curr_symbol}" if isinstance(t_low, (int, float)) else "N/A", delta=f"~ {t_low*eur_rate:.2f} €" if isinstance(t_low, (int, float)) else None)
                a_col3.metric("Ziel Schnitt", f"{t_mean:.2f} {curr_symbol}" if isinstance(t_mean, (int, float)) else "N/A", delta=f"~ {t_mean*eur_rate:.2f} €" if isinstance(t_mean, (int, float)) else None)
                a_col4.metric("Ziel Hoch", f"{t_high:.2f} {curr_symbol}" if isinstance(t_high, (int, float)) else "N/A", delta=f"~ {t_high*eur_rate:.2f} €" if isinstance(t_high, (int, float)) else None)

            # ------------------------------------------
            # TAB 5: DIVIDENDEN
            # ------------------------------------------
            with tab_dividends:
                st.subheader("💰 Dividenden-Analyse")
                div_yield = (info.get('dividendYield') or 0) * 100
                div_rate = info.get('dividendRate') or 0
                payout_ratio = (info.get('payoutRatio') or 0) * 100

                div_col1, div_col2, div_col3, div_col4 = st.columns(4)
                div_col1.metric("Dividendenrendite", f"{div_yield:.2f}%")

                div_rate_eur = div_rate * eur_rate
                if currency_code != "EUR":
                    div_col2.metric("Dividende / Aktie p.a.", f"{div_rate:.2f} {curr_symbol}", delta=f"~ {div_rate_eur:.2f} €")
                else:
                    div_col2.metric("Dividende / Aktie p.a.", f"{div_rate:.2f} €")

                div_col3.metric("Ausschüttungsquote", f"{payout_ratio:.2f}%")

                sample_shares = 100
                est_payout_eur = sample_shares * div_rate_eur
                div_col4.metric(f"Ertrag bei {sample_shares} Stk.", f"{est_payout_eur:.2f} € / Jahr")

                if not dividends_data.empty:
                    st.markdown("#### 📜 Historische Dividendenzahlungen (pro Aktie)")
                    div_df = dividends_data.tail(20).to_frame(name="Ausschüttung")
                    div_df['Ausschüttung (EUR)'] = div_df['Ausschüttung'] * eur_rate

                    fig_div = go.Figure()
                    fig_div.add_trace(go.Bar(
                        x=div_df.index,
                        y=div_df['Ausschüttung (EUR)'],
                        name="Dividende (€)",
                        marker_color="#2ea043"
                    ))
                    fig_div.update_layout(
                        template="plotly_dark",
                        height=350,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        yaxis_title="Betrag in €"
                    )
                    st.plotly_chart(fig_div, use_container_width=True)
                else:
                    st.info("Dieses Unternehmen schüttet aktuell keine Dividende aus.")

            # ------------------------------------------
            # TAB 6: PEER-GROUP
            # ------------------------------------------
            with tab_peers:
                peer_input = st.text_input("Peers eingeben (kommagetrennt):", value=f"{ticker_symbol}, MSFT, GOOGL, NVDA")
                peer_list = list(dict.fromkeys([p.strip().upper() for p in peer_input.split(",") if p.strip()]))
                if st.button("Peers vergleichen", use_container_width=True):
                    with st.spinner("Lade Peer-Daten..."):
                        with ThreadPoolExecutor(max_workers=6) as executor:
                            peer_raw = list(executor.map(load_quick_quote, peer_list))

                    peer_data = []
                    for item in peer_raw:
                        p_sym = item["symbol"]
                        p_inf = item["info"]
                        if not p_inf:
                            continue
                        p_curr = p_inf.get('currency', 'USD')
                        p_rate = get_eur_exchange_rate(p_curr)
                        p_price = p_inf.get('currentPrice') or p_inf.get('regularMarketPrice') or 0
                        peer_data.append({
                            "Symbol": p_sym,
                            "Name": p_inf.get('shortName', p_sym),
                            "Kurs (Original)": f"{p_price:.2f} {p_curr}",
                            "Kurs (EUR €)": f"{p_price * p_rate:.2f} €",
                            "KGV (Fwd)": round(p_inf.get('forwardPE', 0), 2) if p_inf.get('forwardPE') else "N/A",
                            "Nettomarge": f"{(p_inf.get('profitMargins') or 0)*100:.1f}%",
                            "ROE": f"{(p_inf.get('returnOnEquity') or 0)*100:.1f}%"
                        })
                    st.dataframe(pd.DataFrame(peer_data), use_container_width=True, hide_index=True)

            # ------------------------------------------
            # TAB 7: NEWS & TERMINE
            # ------------------------------------------
            with tab_news:
                st.subheader("📅 Anstehende Termine & Quartalszahlen (Earnings)")
                if calendar_data is not None and not (isinstance(calendar_data, pd.DataFrame) and calendar_data.empty):
                    try:
                        cal_dict = calendar_data if isinstance(calendar_data, dict) else calendar_data.to_dict()
                        e_date = cal_dict.get('Earnings Date', ['N/A'])[0] if isinstance(cal_dict.get('Earnings Date'), list) else cal_dict.get('Earnings Date', 'N/A')
                        eps_avg = cal_dict.get('Earnings Average', 'N/A')
                        rev_avg = cal_dict.get('Revenue Average', 'N/A')

                        col_cal1, col_cal2, col_cal3 = st.columns(3)
                        col_cal1.metric("Nächstes Earnings Date", str(e_date))
                        col_cal2.metric("Erwarteter EPS (Schnitt)", str(eps_avg))
                        if isinstance(rev_avg, (int, float)):
                            col_cal3.metric("Erwarteter Umsatz", f"{rev_avg / 1e9:.2f} B {curr_symbol}")
                        else:
                            col_cal3.metric("Erwarteter Umsatz", str(rev_avg))
                    except Exception:
                        st.info("Keine detaillierten Termindaten über API abrufbar.")
                else:
                    st.info("Aktuell stehen keine bevorstehenden Termine fest.")

                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("📰 Aktuelle Unternehmens-News")
                if news_data:
                    for item in news_data[:5]:
                        c = item.get('content', item)
                        title = c.get('title', 'Titel')
                        url = c.get('canonicalUrl', {}).get('url', c.get('link', '#'))
                        provider = c.get('provider', {}).get('displayName', c.get('publisher', 'N/A'))
                        st.markdown(f"**[{title}]({url})**")
                        st.caption(f"Quelle: {provider}")
                        st.markdown("---")
                else:
                    st.info("Keine aktuellen Nachrichten verfügbar.")

            # ------------------------------------------
            # TAB 8: LAGE-ANALYSE
            # ------------------------------------------
            with tab_signals:
                sig_col1, sig_col2 = st.columns(2)
                with sig_col1:
                    st.subheader(f"🚦 Basis-Check ({score} / {max_score})")
                    for status, text in reasons:
                        st.write(f"- **{status}:** {text}")
                with sig_col2:
                    st.subheader(f"🏛️ Piotroski F-Score ({piotroski_score} / 9)")
                    for status, text in piotroski_details:
                        st.write(f"- **{status}:** {text}")

            # ------------------------------------------
            # TAB 9: INTERAKTIVES DCF-MODELL
            # ------------------------------------------
            with tab_dcf:
                st.subheader("🧮 Interaktives DCF-Bewertungsmodell")
                if free_cash_flow_m <= 0:
                    st.warning("Das Unternehmen weist aktuell einen negativen oder fehlenden Free Cash Flow auf. Eine DCF-Bewertung auf FCF-Basis ist daher nicht sinnvoll.")
                else:
                    dcf_c1, dcf_c2 = st.columns([1, 1])
                    with dcf_c1:
                        g_1_5 = st.slider("FCF-Wachstum Jahre 1–5 (% p.a.):", -5.0, 30.0, 10.0, 0.5) / 100
                        g_6_10 = st.slider("FCF-Wachstum Jahre 6–10 (% p.a.):", 0.0, 15.0, 5.0, 0.5) / 100
                        wacc_in = st.slider("Diskontierungssatz / WACC (%):", 5.0, 15.0, 9.0, 0.5) / 100
                        term_mult = st.slider("Terminal FCF-Multiple (Jahr 10):", 8.0, 25.0, 15.0, 1.0)

                    sim_fair_val = calculate_dcf(free_cash_flow_m, net_debt_m, shares_outstanding_m, g_1_5, g_6_10, wacc_in, term_mult)
                    sim_margin = ((sim_fair_val - current_price) / current_price) * 100 if current_price else 0

                    with dcf_c2:
                        st.metric("Simulierter Fairer Wert", f"{sim_fair_val:.2f} {curr_symbol}", delta=f"{sim_margin:+.1f}% vs. Aktueller Kurs")
                        st.metric("Simulierter Wert (EUR)", f"{sim_fair_val * eur_rate:.2f} €")
                        st.caption(f"Basisdaten: Free Cash Flow = {free_cash_flow_m:,.1f} Mio. {curr_symbol} | Nettoverschuldung = {net_debt_m:,.1f} Mio. {curr_symbol}")

            # ------------------------------------------
            # TAB 10: FINANZEN
            # ------------------------------------------
            with tab_finances:
                t1, t2, t3 = st.tabs(["GuV", "Bilanz", "Cashflow"])
                with t1:
                    st.dataframe(financials_df, use_container_width=True)
                with t2:
                    st.dataframe(balance_sheet_df, use_container_width=True)
                with t3:
                    st.dataframe(cashflow_df, use_container_width=True)

        except Exception as e:
            st.error(f"Fehler beim Laden von {ticker_symbol}: {e}")

# ==========================================
# FENSTER 2: WATCHLIST MANAGER
# ==========================================
elif main_nav == "⭐ Watchlist":
    st.markdown("## ⭐ Watchlist Manager")
    st.caption("Verwalte deine favorisierten Aktien mit Live-Kursen in Euro und Tagesveränderungen.")

    if st.session_state.watchlist:
        with st.spinner("Aktualisiere Watchlist..."):
            with ThreadPoolExecutor(max_workers=8) as executor:
                wl_raw = list(executor.map(load_quick_quote, st.session_state.watchlist))

        wl_data = []
        for item in wl_raw:
            w_sym = item["symbol"]
            w_inf = item["info"]
            w_curr = w_inf.get('currency', 'USD')
            w_rate = get_eur_exchange_rate(w_curr)

            price_val = w_inf.get('currentPrice') or w_inf.get('regularMarketPrice') or 0
            prev_close = w_inf.get('previousClose') or price_val

            if price_val and prev_close:
                change_abs = price_val - prev_close
                change_pct = (change_abs / prev_close) * 100
                price_eur = price_val * w_rate
                change_abs_eur = change_abs * w_rate

                icon = "🟢" if change_pct >= 0 else "🔴"
                change_str_orig = f"{icon} {change_abs:+.2f} {w_curr} ({change_pct:+.2f}%)"
                change_str_eur = f"{icon} {change_abs_eur:+.2f} € ({change_pct:+.2f}%)"
            else:
                price_eur = 0
                change_str_orig = "N/A"
                change_str_eur = "N/A"

            wl_data.append({
                "Symbol": w_sym,
                "Name": w_inf.get('shortName', w_sym),
                "Kurs (EUR €)": f"{price_eur:.2f} €" if price_eur else "N/A",
                "Tagesveränderung (€)": change_str_eur,
                "Kurs (Original)": f"{price_val:.2f} {w_curr}" if price_val else "N/A",
                "Tagesveränderung (Original)": change_str_orig,
                "Forward KGV": round(w_inf.get('forwardPE', 0), 2) if w_inf.get('forwardPE') else "N/A",
                "Branche": w_inf.get('industry', 'N/A')
            })

        st.dataframe(pd.DataFrame(wl_data), use_container_width=True, hide_index=True)

        col_wl1, col_wl2 = st.columns([1, 1])
        with col_wl1:
            remove_sym = st.selectbox("Aktie aus Watchlist entfernen:", st.session_state.watchlist)
            if st.button("❌ Ausgewählte Aktie entfernen", use_container_width=True):
                st.session_state.watchlist.remove(remove_sym)
                st.rerun()

        with col_wl2:
            st.markdown("<br>", unsafe_allow_html=True)
            wl_df = pd.DataFrame({"Symbol": st.session_state.watchlist})
            csv_data = wl_df.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Watchlist als CSV Exportieren", data=csv_data, file_name="watchlist.csv", mime="text/csv", use_container_width=True)
    else:
        st.info("Deine Watchlist ist aktuell leer.")

# ==========================================
# FENSTER 3: AKTIEN-SCREENER (INKL. ATR & POC)
# ==========================================
elif main_nav == "🔍 Aktien-Screener":
    st.markdown("## 🔍 Aktien-Screener & Tages-Einstiege")
    st.caption("Durchsuche Märkte nach fundamentaler Stärke, Volume-Supports und ATR-Einstiegszonen.")

    col_sel1, col_sel2 = st.columns([1, 2])
    with col_sel1:
        selected_preset = st.selectbox("Aktien-Gruppe:", list(SCREENER_LISTS.keys()))
        custom_symbols_input = st.text_area("Oder Symbole eingeben:", value=", ".join(SCREENER_LISTS[selected_preset]))

        signal_filter = st.multiselect(
            "Tages-Einstiegssignale filtern (optional):",
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

    with col_sel2:
        min_score = st.slider("Mindest-Score (0–5):", 0, 5, 2)
        max_pe = st.number_input("Maximales Forward KGV:", value=40.0, step=5.0)

    if st.button("🚀 Screening starten", use_container_width=True):
        symbols_to_scan = list(dict.fromkeys([s.strip().upper() for s in custom_symbols_input.split(",") if s.strip()]))
        results = []

        with st.spinner(f"Scanne {len(symbols_to_scan)} Aktien parallel..."):
            with ThreadPoolExecutor(max_workers=8) as executor:
                scanned_items = list(executor.map(load_quick_quote, symbols_to_scan))

        for item in scanned_items:
            sym = item["symbol"]
            inf = item["info"]
            df_h = item["hist"]

            if df_h.empty or len(df_h) < 50:
                continue

            f_pe = inf.get('forwardPE') or 999
            margin = (inf.get('profitMargins') or 0) * 100
            roe_sc = (inf.get('returnOnEquity') or 0) * 100
            price = inf.get('currentPrice') or inf.get('regularMarketPrice') or df_h['Close'].iloc[-1]
            s_curr = inf.get('currency', 'USD')
            s_rate = get_eur_exchange_rate(s_curr)

            ez = analyze_entry_zones(df_h, price)
            if not ez["valid"]:
                continue

            last_c = df_h['Close'].iloc[-1]
            last_s200 = ez["last_sma200"]
            last_r = ez["last_rsi"]
            atr_val = ez["atr_14"]
            poc_val = ez["poc_price"]
            avwap_val = ez["last_avwap"]

            vol_sma20 = df_h['Volume'].rolling(20).mean()
            last_vol = df_h['Volume'].iloc[-1]
            avg_vol = vol_sma20.iloc[-1]
            high_20d = df_h['High'].iloc[-21:-1].max() if len(df_h) > 21 else df_h['High'].max()

            c_score = 0
            if last_c > last_s200:
                c_score += 1
            if last_r < 35:
                c_score += 1
            if 0 < f_pe < 25:
                c_score += 1
            if margin > 12:
                c_score += 1
            if roe_sc > 12:
                c_score += 1

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

            match_signal_filter = True
            if "🔥 Volumen-Ausbruch (> 1.5x Ø Vol)" in signal_filter and "🔥 Vol-Spike" not in today_signals:
                match_signal_filter = False
            if "📈 20-Tage-Hoch Durchbruch" in signal_filter and "📈 20D-Breakout" not in today_signals:
                match_signal_filter = False
            if "📉 RSI Überverkauft (< 35)" in signal_filter and "📉 RSI Oversold" not in today_signals:
                match_signal_filter = False
            if "🎯 Nahe 200-SMA Support (±1 ATR)" in signal_filter and "🎯 200-SMA Support" not in today_signals:
                match_signal_filter = False
            if "📊 Nahe Volume POC (±1 ATR)" in signal_filter and "📊 Volume POC" not in today_signals:
                match_signal_filter = False
            if "⚓ Nahe Anchored VWAP (±1 ATR)" in signal_filter and "⚓ Anchored VWAP" not in today_signals:
                match_signal_filter = False

            if c_score >= min_score and f_pe <= max_pe and match_signal_filter:
                results.append({
                    "Symbol": sym,
                    "Name": inf.get('shortName', sym),
                    "Tages-Signal": ", ".join(today_signals) if today_signals else "➖ Konsolidierung",
                    "Konfluenz": f"{ez['confluence_count']} Akt.",
                    "Score": f"{c_score} / 5",
                    "Kurs (EUR €)": f"{price * s_rate:.2f} €" if price else "N/A",
                    "Volume POC": f"{poc_val * s_rate:.2f} €",
                    "Abstand 200-SMA": f"{ez['atr_dist_sma200']:+.1f}x ATR",
                    "Forward KGV": round(f_pe, 2) if f_pe != 999 else "N/A",
                    "RSI (14)": round(last_r, 1)
                })

        if results:
            st.success(f"Gefunden: {len(results)} Aktien entsprechen deinen Kriterien!")
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        else:
            st.warning("Keine Treffer mit diesen Kriterien gefunden.")

# ==========================================
# FENSTER 4: MARKTANALYSE & FEAR/GREED INDEX
# ==========================================
elif main_nav == "🌐 Markt & Zukunft":
    st.markdown("## 🌐 Globale Markt-Analyse & Fear & Greed Index")
    st.caption("Einordnung der aktuellen Marktstimmung, Volatilität und Branchen-Performance.")

    with st.spinner("Lade globale Marktdaten..."):
        try:
            sp500, vix, dax, sector_data = load_market_overview()

            last_sp500 = sp500['Close'].iloc[-1]
            sp500_sma200 = ta.trend.sma_indicator(sp500['Close'], window=200).iloc[-1]
            vix_level = vix['Close'].iloc[-1] if not vix.empty else 20.0
            sp500_rsi = ta.momentum.rsi(sp500['Close'], window=14).iloc[-1]

            vix_score = max(0, min(100, (35 - vix_level) * 4))
            rsi_score = sp500_rsi
            mom_diff = ((last_sp500 - sp500_sma200) / sp500_sma200) * 100
            mom_score = max(0, min(100, 50 + (mom_diff * 5)))

            fg_index = int((vix_score * 0.4) + (rsi_score * 0.3) + (mom_score * 0.3))

            if fg_index <= 25:
                fg_status = "😱 Extreme Angst (Extreme Fear)"
            elif fg_index <= 45:
                fg_status = "😨 Angst (Fear)"
            elif fg_index <= 55:
                fg_status = "😐 Neutral"
            elif fg_index <= 75:
                fg_status = "🤑 Gier (Greed)"
            else:
                fg_status = "🔥 Extreme Gier (Extreme Greed)"

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)

            with col_m1:
                st.metric("Fear & Greed Index", f"{fg_index} / 100", delta=fg_status)

            with col_m2:
                sp500_status = "🟢 Bullenmarkt (> 200-SMA)" if last_sp500 > sp500_sma200 else "🔴 Bärenmarkt (< 200-SMA)"
                st.metric("S&P 500 Haupttrend", f"{last_sp500:,.0f} Pkt.", delta=sp500_status)

            with col_m3:
                if vix_level < 15:
                    vix_status = "🟢 Entspannt"
                elif vix_level < 25:
                    vix_status = "🟡 Moderat"
                else:
                    vix_status = "🔴 Panik"
                st.metric("VIX Volatilität", f"{vix_level:.1f}", delta=vix_status)

            with col_m4:
                last_dax = dax['Close'].iloc[-1]
                dax_sma200 = ta.trend.sma_indicator(dax['Close'], window=200).iloc[-1]
                dax_status = "🟢 Aufwärtstrend" if last_dax > dax_sma200 else "🔴 Abwärtstrend"
                st.metric("DAX Index", f"{last_dax:,.0f} Pkt.", delta=dax_status)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🔮 Makro-Zukunftsausblick")

            if fg_index <= 25:
                st.info("""
                **Gesamtbild: EXTREME ANGST (Kaufchancen antizyklisch)**
                * **Stimmung:** Der Markt ist überverkauft und von Panik geprägt.
                * **Strategie:** Historisch gesehen bieten Phasen extremer Angst hervorragende Einstiegsgelegenheiten für langfristige Anleger.
                """)
            elif fg_index >= 75:
                st.warning("""
                **Gesamtbild: EXTREME GIER (Überhitzt / Vorsicht)**
                * **Stimmung:** Anleger sind sehr sorglos, die Kurse sind stark gestiegen.
                * **Strategie:** Gewinne sichern, Stop-Loss nachziehen und keine überhitzten Aktien mehr nachkaufen.
                """)
            else:
                st.success("""
                **Gesamtbild: MODERATES MARKTUMFELD**
                * **Stimmung:** Der Markt zeigt eine ausgeglichene Bewegung ohne extreme Ausschläge.
                * **Strategie:** Einzelwertanalyse (Stock-Picking) nach Fundamentaldaten fokussieren.
                """)

            st.markdown("---")
            st.markdown("### 📊 Sektor-Rotation (Performance 1 Monat)")

            if sector_data:
                df_sectors = pd.DataFrame(sector_data).sort_values(by="Performance (%)", ascending=False)
                fig_sec = go.Figure(go.Bar(
                    x=df_sectors['Performance (%)'],
                    y=df_sectors['Sektor'],
                    orientation='h',
                    marker_color=['#2ea043' if val >= 0 else '#f85149' for val in df_sectors['Performance (%)']]
                ))
                fig_sec.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title="Veränderung in %")
                st.plotly_chart(fig_sec, use_container_width=True)

        except Exception as e:
            st.error(f"Fehler bei der Marktanalyse: {e}")
