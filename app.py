import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta
import time
import io
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Seiten-Konfiguration
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
    /* Haupt-Hintergrund und Schriften */
    .stApp {
        background-color: #0e1117;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #21262d;
    }

    /* Metric Cards - Dezent und flach */
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
    
    /* Native Container (z.B. PDF-Export Kasten) */
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
    
    /* Executive Banner Cards - Schlichter Accent-Border */
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

    /* Clean Tabs Navigation */
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

    /* Schlichte Buttons */
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
    
    /* Typografie Dezent halten */
    h1, h2, h3 {
        color: #f0f6fc !important;
        font-weight: 600 !important;
        letter-spacing: -0.3px;
    }
</style>
""", unsafe_allow_html=True)

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
        "AIXA.DE", "NEM.DE", "SRT3.DE", "HAG.DE", "ENR.DE", "SOW.DE", "DEQ.DE"
    ],
    "Euro Stoxx 50 (Europa)": [
        "ASML.AS", "MC.PA", "SAP.DE", "OR.PA", "TTE.PA", "SIE.DE", "ALV.DE", "SU.PA", 
        "SAN.MC", "SAN.PA", "CDI.PA", "IBE.MC", "BNP.PA", "AIR.PA", "ENEL.MI", "BBVA.MC"
    ],
    "Dividenden-Aristokraten": [
        "JNJ", "PG", "KO", "PEP", "MMM", "ABBV", "CVX", "XOM", "TGT", "LOW", 
        "EMR", "ITW", "O", "ADP", "GD", "MCD", "WMT", "NOK", "CL"
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

# ==========================================
# CACHING-FUNKTIONEN (INKL. WECHSELKURS)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_eur_exchange_rate(currency):
    """Liefert den Umrechnungsfaktor von der Zielwährung in EUR"""
    if not currency or currency.upper() in ["EUR", "EUR="]:
        return 1.0
    try:
        pair = f"{currency.upper()}EUR=X"
        fx_ticker = yf.Ticker(pair)
        fx_data = fx_ticker.history(period="1d")
        if not fx_data.empty:
            return float(fx_data['Close'].iloc[-1])
        
        # Fallback invertiert
        inv_pair = f"EUR{currency.upper()}=X"
        inv_ticker = yf.Ticker(inv_pair)
        inv_data = inv_ticker.history(period="1d")
        if not inv_data.empty:
            return 1.0 / float(inv_data['Close'].iloc[-1])
    except Exception:
        pass
    return 1.0

@st.cache_data(ttl=900, show_spinner=False)
def load_stock_data(symbol):
    ticker = yf.Ticker(symbol)
    info = ticker.info
    df_daily = ticker.history(period="1y")
    cashflow_df = ticker.cashflow
    financials_df = ticker.financials
    balance_sheet_df = ticker.balance_sheet
    
    try:
        news_data = ticker.news
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

# ==========================================
# ROBUSTE SUCHE MIT YFINANCE
# ==========================================
def search_ticker(query):
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
# PIOTROSKI F-SCORE BERECHNUNG
# ==========================================
def calculate_piotroski_score(financials, balance_sheet, cashflow):
    score = 0
    details = []
    try:
        if financials.empty or balance_sheet.empty or cashflow.empty:
            return 0, [("🟡 Info", "Unvollständige Bilanzen für F-Score")]
            
        net_income = financials.loc['Net Income'].iloc[0] if 'Net Income' in financials.index else 0
        if net_income > 0:
            score += 1
            details.append(("🟢 F1 - Profitabilität", "Positives Nettoeinkommen"))
        else:
            details.append(("🔴 F1 - Profitabilität", "Negatives Nettoeinkommen"))
            
        ocf = cashflow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cashflow.index else 0
        if ocf > 0:
            score += 1
            details.append(("🟢 F2 - Cashflow", "Positiver operativer Cashflow"))
        else:
            details.append(("🔴 F2 - Cashflow", "Negativer operativer Cashflow"))
            
        tot_assets = balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.index else 1
        tot_assets_prev = balance_sheet.loc['Total Assets'].iloc[1] if 'Total Assets' in balance_sheet.index and len(balance_sheet.columns) > 1 else tot_assets
        roa_curr = net_income / tot_assets
        net_inc_prev = financials.loc['Net Income'].iloc[1] if 'Net Income' in financials.index and len(financials.columns) > 1 else 0
        roa_prev = net_inc_prev / tot_assets_prev
        
        if roa_curr > roa_prev:
            score += 1
            details.append(("🟢 F3 - ROA Dynamik", f"ROA gestiegen ({roa_curr*100:.1f}% vs {roa_prev*100:.1f}%)"))
        else:
            details.append(("🔴 F3 - ROA Dynamik", "ROA gesunken oder stagniert"))
            
        if ocf > net_income:
            score += 1
            details.append(("🟢 F4 - Gewinnqualität", "Operativer Cashflow ist höher als der Bilanzgewinn"))
        else:
            details.append(("🔴 F4 - Gewinnqualität", "Bilanzgewinn höher als tatsächlicher Cashflow"))

        lt_debt_curr = balance_sheet.loc['Long Term Debt'].iloc[0] if 'Long Term Debt' in balance_sheet.index else 0
        lt_debt_prev = balance_sheet.loc['Long Term Debt'].iloc[1] if 'Long Term Debt' in balance_sheet.index and len(balance_sheet.columns) > 1 else lt_debt_curr
        if lt_debt_curr <= lt_debt_prev:
            score += 1
            details.append(("🟢 F5 - Verschuldung", "Langfristige Schulden gesunken oder gleich geblieben"))
        else:
            details.append(("🔴 F5 - Verschuldung", "Langfristige Schulden gestiegen"))

    except Exception:
        return score, details
        
    return score, details

# ==========================================
# PDF-REPORT GENERATOR
# ==========================================
def generate_pdf_report(symbol, company_name, current_price, fair_value, score, piotroski_score, reasons, currency_symbol, eur_rate):
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
        ["DCF Fairer Wert", f"{fair_value:.2f} {currency_symbol}", f"{fair_value * eur_rate:.2f} €"],
        ["Gesamt-Score", f"{score} / 6 Punkte", "-"],
        ["Piotroski F-Score", f"{piotroski_score} / 5 Punkte", "-"]
    ]
    
    t = Table(data, colWidths=[150, 150, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0E1117")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    story.append(t)
    story.append(Spacer(1, 18))

    story.append(Paragraph("<b>Detail-Bewertungen:</b>", styles['Heading2']))
    for status, text in reasons:
        story.append(Paragraph(f"• <b>{status}:</b> {text}", styles['Normal']))
        story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# SEITENLEISTE: NAVIGATION & FAVORITEN (MIT EUR-KURS & TAGESVERÄNDERUNG)
# ==========================================
st.sidebar.markdown("## 🤑 GEILEPROFITE")

main_nav = st.sidebar.radio(
    "",
    ["📊 Aktien-Analyse", "⭐ Watchlist", "🔍 Aktien-Screener", "🌐 Markt & Zukunft"]
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
    for w_sym in st.session_state.watchlist[:5]:
        try:
            w_t = yf.Ticker(w_sym)
            w_inf = w_t.info
            
            w_curr = w_inf.get('currency', 'USD').upper()
            w_rate = get_eur_exchange_rate(w_curr)
            
            price_val = w_inf.get('currentPrice', w_inf.get('regularMarketPrice', 0))
            prev_close = w_inf.get('previousClose', price_val)
            
            if price_val and prev_close:
                change_pct = ((price_val - prev_close) / prev_close) * 100
                price_eur = price_val * w_rate
                icon = "🟢" if change_pct >= 0 else "🔴"
                label_str = f"{w_sym} | {price_eur:.2f} € ({icon} {change_pct:+.1f}%)"
            else:
                label_str = f"{w_sym}"
        except Exception:
            label_str = f"{w_sym}"

        if st.sidebar.button(label_str, key=f"fav_btn_{w_sym}", use_container_width=True):
            st.session_state.active_ticker = w_sym
            st.rerun()


# ==========================================
# FENSTER 1: AKTIEN-ANALYSE
# ==========================================
if main_nav == "📊 Aktien-Analyse":
    
    # UNTERNEHMENSSUCHE
    col_search1, col_search2 = st.columns([3, 1])
    
    with col_search1:
        search_input = st.text_input(
            "Suchbegriff oder Ticker-Symbol:", 
            placeholder="z. B. Apple, NVDA, SAP.DE, TSLA...",
            label_visibility="collapsed"
        )
        
    with col_search2:
        btn_search = st.button("🔍 Suchen", use_container_width=True)

    if search_input and (btn_search or search_input):
        search_results = search_ticker(search_input)
        if search_results:
            selected_option = st.selectbox(
                "Suchergebnisse (wählen zum Analysieren):",
                options=[opt[0] for opt in search_results],
                key="select_search_result"
            )
            for label, sym in search_results:
                if label == selected_option:
                    if st.session_state.active_ticker != sym:
                        st.session_state.active_ticker = sym
                        st.rerun()
        else:
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
                ticker = yf.Ticker(ticker_symbol)

            company_name = info.get('longName', ticker_symbol)
            currency_code = info.get('currency', 'USD').upper()
            curr_symbol = "$" if currency_code == "USD" else ("€" if currency_code == "EUR" else currency_code)
            
            # Umrechnungskurs ermitteln
            eur_rate = get_eur_exchange_rate(currency_code)

            st.markdown(f"## {company_name} <span style='color:#8b949e; font-size: 20px;'>({info.get('symbol', ticker_symbol)})</span>", unsafe_allow_html=True)
            st.caption(f"**Branche:** {info.get('industry', 'N/A')} | **Sektor:** {info.get('sector', 'N/A')} | **Währung:** {currency_code} (Wechselkurs zu EUR: {eur_rate:.4f})")
            
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            kgv = info.get('forwardPE', 'N/A')
            marge = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 'N/A'
            roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 'N/A'
            beta = info.get('beta', 'N/A')
            
            has_tech_data = not df_daily.empty and len(df_daily) >= 200
            
            if has_tech_data:
                df_daily['SMA_50'] = ta.trend.sma_indicator(df_daily['Close'], window=50)
                df_daily['SMA_200'] = ta.trend.sma_indicator(df_daily['Close'], window=200)
                df_daily['RSI'] = ta.momentum.rsi(df_daily['Close'], window=14)
                
                bb = ta.volatility.BollingerBands(close=df_daily['Close'], window=20, window_dev=2)
                df_daily['BB_high'] = bb.bollinger_hband()
                df_daily['BB_low'] = bb.bollinger_lband()
                
                macd = ta.trend.MACD(close=df_daily['Close'])
                df_daily['MACD'] = macd.macd()
                df_daily['MACD_signal'] = macd.macd_signal()
                df_daily['MACD_diff'] = macd.macd_diff()
                
                last_close = df_daily['Close'].iloc[-1]
                last_sma50 = df_daily['SMA_50'].iloc[-1]
                last_sma200 = df_daily['SMA_200'].iloc[-1]
                last_rsi = df_daily['RSI'].iloc[-1]
                
                low_52 = df_daily['Low'].min()
                high_52 = df_daily['High'].max()
                entry_ideal_low = last_sma200 * 0.95 if last_sma200 > 0 else low_52
                entry_ideal_high = last_sma200 * 1.02 if last_sma200 > 0 else low_52 * 1.10
            else:
                last_close = current_price
                last_sma50 = last_sma200 = last_rsi = low_52 = high_52 = 0
                entry_ideal_low = entry_ideal_high = 0

            # DCF Vorberechnung
            free_cash_flow = 0
            if not cashflow_df.empty and 'Free Cash Flow' in cashflow_df.index:
                free_cash_flow = cashflow_df.loc['Free Cash Flow'].iloc[0] / 1e6
            
            shares_outstanding = info.get('sharesOutstanding', 1) / 1e6
            total_debt = info.get('totalDebt', 0) / 1e6
            total_cash = info.get('totalCash', 0) / 1e6
            net_debt = total_debt - total_cash

            fcf_curr = free_cash_flow if free_cash_flow != 0 else 1000.0
            disc_fcf_list = []
            p_fcf = fcf_curr
            for y in range(1, 11):
                r = 0.10 if y <= 5 else 0.05
                p_fcf *= (1 + r)
                disc_fcf_list.append(p_fcf / ((1 + 0.09) ** y))
            
            tv = p_fcf * 15.0
            disc_tv = tv / ((1 + 0.09) ** 10)
            eq_val = (sum(disc_fcf_list) + disc_tv) - net_debt
            dcf_fair_value = eq_val / shares_outstanding if shares_outstanding > 0 else 0
            dcf_margin = ((dcf_fair_value - current_price) / current_price) * 100 if current_price else 0

            piotroski_score, piotroski_details = calculate_piotroski_score(financials_df, balance_sheet_df, cashflow_df)

            score = 0
            max_score = 6
            reasons = []

            if has_tech_data:
                if last_close > last_sma200:
                    score += 1
                    reasons.append(("🟢 Positiv", "Kurs über SMA 200 (Aufwärtstrend)"))
                else:
                    reasons.append(("🔴 Negativ", "Kurs unter SMA 200 (Abwärtstrend)"))

                if last_rsi < 35:
                    score += 1
                    reasons.append(("🟢 Positiv", f"RSI bei {last_rsi:.1f} (Überverkauft - Kaufchance)"))
                elif last_rsi > 65:
                    reasons.append(("🔴 Negativ", f"RSI bei {last_rsi:.1f} (Überkauft)"))
                else:
                    reasons.append(("🟡 Neutral", f"RSI im neutralen Bereich ({last_rsi:.1f})"))

                if last_sma50 > last_sma200:
                    score += 1
                    reasons.append(("🟢 Positiv", "Golden Cross aktiv (SMA 50 > SMA 200)"))
                else:
                    reasons.append(("🔴 Negativ", "Death Cross aktiv (SMA 50 < SMA 200)"))

            forward_pe = info.get('forwardPE', None)
            if forward_pe and forward_pe < 20:
                score += 1
                reasons.append(("🟢 Positiv", f"Moderates Forward-KGV ({forward_pe:.1f})"))
            elif forward_pe:
                reasons.append(("🟡 Neutral/Teuer", f"Hohes Forward-KGV ({forward_pe:.1f})"))

            margin_val = info.get('profitMargins', 0)
            if margin_val and margin_val > 0.15:
                score += 1
                reasons.append(("🟢 Positiv", f"Starke Nettomarge ({margin_val*100:.1f}%)"))
            else:
                reasons.append(("🔴 Negativ", "Geringe/Negative Nettomarge (< 15%)"))

            roe_val = info.get('returnOnEquity', 0)
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
                st.metric("Gesamt-Score", f"{score} / {max_score} Pkt.", delta=f"Piotroski: {piotroski_score}/5")

            with b_col3:
                dcf_eur = dcf_fair_value * eur_rate
                delta_str = f"{dcf_margin:+.1f}% vs. Kurs"
                if currency_code != "EUR":
                    st.metric("DCF Fairer Wert", f"{dcf_fair_value:.2f} {curr_symbol}", delta=f"~ {dcf_eur:.2f} € | {delta_str}")
                else:
                    st.metric("DCF Fairer Wert", f"{dcf_fair_value:.2f} €", delta=delta_str)

            with b_col4:
                pdf_bytes = generate_pdf_report(ticker_symbol, company_name, current_price, dcf_fair_value, score, piotroski_score, reasons, curr_symbol, eur_rate)
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
                
            col2.metric("Forward KGV", f"{kgv:.2f}" if isinstance(kgv, (int, float)) else kgv)
            col3.metric("Nettomarge", f"{marge:.2f}%" if isinstance(marge, (int, float)) else marge)
            col4.metric("Beta (S&P 500)", f"{beta:.2f}" if isinstance(beta, (int, float)) else str(beta))

            st.markdown("<br>", unsafe_allow_html=True)

            # Unter-Tabs
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

            with tab_chart:
                st.subheader("Kursverlauf & Indikatoren")
                
                # Auswahl von Zeitraum und Intervall
                col_tf1, col_tf2 = st.columns(2)
                with col_tf1:
                    timeframe = st.selectbox(
                        "Zeitraum:", 
                        ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], 
                        index=3
                    )
                with col_tf2:
                    if timeframe == "1d":
                        interval_options = ["1m", "2m", "5m", "15m", "30m", "60m"]
                        default_idx = 2  # 5m
                    elif timeframe == "5d":
                        interval_options = ["5m", "15m", "30m", "60m", "1d"]
                        default_idx = 1  # 15m
                    else:
                        interval_options = ["1d", "1wk", "1mo"]
                        default_idx = 0  # 1d
                        
                    interval = st.selectbox("Intervall (Auflösung):", interval_options, index=default_idx)

                hist = ticker.history(period=timeframe, interval=interval)
                
                if not hist.empty:
                    show_bb = st.checkbox("Bollinger Bänder anzeigen", value=True)
                    
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                    
                    fig.add_trace(go.Candlestick(
                        x=hist.index, 
                        open=hist['Open'], 
                        high=hist['High'], 
                        low=hist['Low'], 
                        close=hist['Close'], 
                        name=f"Kurs ({curr_symbol})"
                    ), row=1, col=1)
                    
                    if show_bb and 'BB_high' in df_daily.columns and timeframe not in ["1d", "5d"]:
                        fig.add_trace(go.Scatter(x=df_daily.index, y=df_daily['BB_high'], line=dict(color='rgba(255, 255, 255, 0.3)'), name="BB Oben"), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df_daily.index, y=df_daily['BB_low'], line=dict(color='rgba(255, 255, 255, 0.3)'), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)', name="BB Unten"), row=1, col=1)

                    if 'MACD' in df_daily.columns and timeframe not in ["1d", "5d"]:
                        fig.add_trace(go.Scatter(x=df_daily.index, y=df_daily['MACD'], line=dict(color='#58a6ff'), name="MACD"), row=2, col=1)
                        fig.add_trace(go.Scatter(x=df_daily.index, y=df_daily['MACD_signal'], line=dict(color='#f59e0b'), name="Signal"), row=2, col=1)
                        colors_macd = ['#10b981' if val >= 0 else '#ef4444' for val in df_daily['MACD_diff']]
                        fig.add_trace(go.Bar(x=df_daily.index, y=df_daily['MACD_diff'], marker_color=colors_macd, name="Hist"), row=2, col=1)

                    fig.update_layout(
                        xaxis_rangeslider_visible=False, 
                        template="plotly_dark", 
                        height=600, 
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Keine Intraday-Daten für dieses Intervall verfügbar.")

            with tab_entry:
                if has_tech_data:
                    ez_col1, ez_col2 = st.columns([1, 1])
                    with ez_col1:
                        st.info(f"**Aktueller Kurs:** {current_price:.2f} {curr_symbol} (~ {current_price*eur_rate:.2f} €)")
                        st.success(f"**🟢 Kaufzone (200-SMA):** {entry_ideal_low:.2f} {curr_symbol} – {entry_ideal_high:.2f} {curr_symbol} (~ {entry_ideal_low*eur_rate:.2f} € – {entry_ideal_high*eur_rate:.2f} €)")
                        st.warning(f"**🟡 52-Wochen-Tief:** {low_52:.2f} {curr_symbol} (~ {low_52*eur_rate:.2f} €)")
                        st.error(f"**🔴 52-Wochen-Hoch:** {high_52:.2f} {curr_symbol} (~ {high_52*eur_rate:.2f} €)")
                    with ez_col2:
                        fig_entry = go.Figure()
                        fig_entry.add_trace(go.Scatter(x=df_daily.index, y=df_daily['Close'], mode='lines', name='Kurs'))
                        fig_entry.add_trace(go.Scatter(x=df_daily.index, y=df_daily['SMA_200'], mode='lines', name='200-SMA', line=dict(dash='dash', color='orange')))
                        fig_entry.add_hrect(y0=entry_ideal_low, y1=entry_ideal_high, fillcolor="green", opacity=0.15, line_width=0)
                        fig_entry.update_layout(template="plotly_dark", height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_entry, use_container_width=True)

            with tab_risk:
                st.subheader("🛡️ Risk & Positionsgrößen-Rechner")
                p_col1, p_col2 = st.columns([1, 1])
                with p_col1:
                    account_size_eur = st.number_input("Gesamtes Depotkapital (€):", value=10000.0, step=1000.0)
                    risk_pct = st.slider("Maximales Risiko pro Trade (%):", 0.5, 5.0, 1.0, 0.5) / 100
                    stop_loss_curr = st.number_input(f"Geplanter Stop-Loss Preis ({curr_symbol}):", value=float(current_price * 0.95), step=1.0)
                
                risk_amount_eur = account_size_eur * risk_pct
                risk_per_share_curr = current_price - stop_loss_curr
                risk_per_share_eur = risk_per_share_curr * eur_rate
                
                with p_col2:
                    if risk_per_share_curr > 0:
                        position_shares = int(risk_amount_eur / risk_per_share_eur)
                        position_value_curr = position_shares * current_price
                        position_value_eur = position_value_curr * eur_rate
                        
                        st.success(f"**Empfohlene Kaufmenge:** {position_shares} Aktien")
                        st.metric("Positionsvolumen", f"{position_value_eur:,.2f} €", delta=f"{position_value_curr:,.2f} {curr_symbol}")
                        st.metric("Maximaler Verlust bei Stop-Loss", f"{risk_amount_eur:,.2f} €")
                    else:
                        st.error("Der Stop-Loss muss unter dem aktuellen Kurs liegen!")

            with tab_analysts:
                t_low = info.get('targetLowPrice', 'N/A')
                t_mean = info.get('targetMeanPrice', 'N/A')
                t_high = info.get('targetHighPrice', 'N/A')
                rec = info.get('recommendationKey', 'N/A').upper()
                a_col1, a_col2, a_col3, a_col4 = st.columns(4)
                a_col1.metric("Konsens", rec)
                a_col2.metric("Ziel Tief", f"{t_low:.2f} {curr_symbol}" if isinstance(t_low, (int, float)) else str(t_low), delta=f"~ {t_low*eur_rate:.2f} €" if isinstance(t_low, (int, float)) else None)
                a_col3.metric("Ziel Schnitt", f"{t_mean:.2f} {curr_symbol}" if isinstance(t_mean, (int, float)) else str(t_mean), delta=f"~ {t_mean*eur_rate:.2f} €" if isinstance(t_mean, (int, float)) else None)
                a_col4.metric("Ziel Hoch", f"{t_high:.2f} {curr_symbol}" if isinstance(t_high, (int, float)) else str(t_high), delta=f"~ {t_high*eur_rate:.2f} €" if isinstance(t_high, (int, float)) else None)

            with tab_dividends:
                div_yield = (info.get('dividendYield', 0) or 0) * 100
                payout_ratio = (info.get('payoutRatio', 0) or 0) * 100
                st.metric("Dividendenrendite", f"{div_yield:.2f}%")
                st.metric("Ausschüttungsquote", f"{payout_ratio:.2f}%")
                if not dividends_data.empty:
                    st.line_chart(dividends_data.tail(20))

            with tab_peers:
                peer_input = st.text_input("Peers eingeben:", value=f"{ticker_symbol}, MSFT, GOOGL, NVDA")
                peer_list = [p.strip().upper() for p in peer_input.split(",") if p.strip()]
                if st.button("Peers vergleichen", use_container_width=True):
                    peer_data = []
                    for p_sym in peer_list:
                        try:
                            p_inf = yf.Ticker(p_sym).info
                            p_curr = p_inf.get('currency', 'USD').upper()
                            p_rate = get_eur_exchange_rate(p_curr)
                            p_price = p_inf.get('currentPrice', p_inf.get('regularMarketPrice', 0))
                            peer_data.append({
                                "Symbol": p_sym,
                                "Kurs (Original)": f"{p_price:.2f} {p_curr}",
                                "Kurs (EUR €)": f"{p_price * p_rate:.2f} €",
                                "KGV (Fwd)": round(p_inf.get('forwardPE', 0), 2) if p_inf.get('forwardPE') else "N/A",
                                "Nettomarge": f"{(p_inf.get('profitMargins', 0) or 0)*100:.1f}%",
                                "ROE": f"{(p_inf.get('returnOnEquity', 0) or 0)*100:.1f}%"
                            })
                        except Exception: continue
                    st.dataframe(pd.DataFrame(peer_data), use_container_width=True)

            with tab_news:
                if news_data:
                    for item in news_data[:5]:
                        c = item.get('content', {})
                        st.markdown(f"**[{c.get('title', 'Titel')}]({c.get('canonicalUrl', {}).get('url', '#')})**")
                        st.caption(f"Quelle: {c.get('provider', {}).get('displayName', 'N/A')}")
                        st.markdown("---")

            with tab_signals:
                st.write(f"**Score:** {score} / {max_score}")
                for status, text in reasons: st.write(f"- **{status}:** {text}")

            with tab_dcf:
                st.write(f"**Berechneter DCF Wert:** {dcf_fair_value:.2f} {curr_symbol} (~ {dcf_fair_value * eur_rate:.2f} €)")

            with tab_finances:
                t1, t2, t3 = st.tabs(["GuV", "Bilanz", "Cashflow"])
                with t1: st.dataframe(financials_df, use_container_width=True)
                with t2: st.dataframe(balance_sheet_df, use_container_width=True)
                with t3: st.dataframe(cashflow_df, use_container_width=True)

        except Exception as e:
            st.error(f"Fehler beim Laden von {ticker_symbol}: {e}")

# ==========================================
# FENSTER 2: WATCHLIST MANAGER (MIT EURO-UMRECHNUNG & TAGESVERÄNDERUNG)
# ==========================================
elif main_nav == "⭐ Watchlist":
    st.markdown("## ⭐ Watchlist Manager")
    st.caption("Verwalte deine favorisierten Aktien mit Live-Kursen in Euro und Tagesveränderungen.")

    if st.session_state.watchlist:
        wl_data = []
        for w_sym in st.session_state.watchlist:
            try:
                w_t = yf.Ticker(w_sym)
                w_inf = w_t.info
                
                w_curr = w_inf.get('currency', 'USD').upper()
                w_rate = get_eur_exchange_rate(w_curr)
                
                price_val = w_inf.get('currentPrice', w_inf.get('regularMarketPrice', 0))
                prev_close = w_inf.get('previousClose', price_val)
                
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
            except Exception:
                wl_data.append({
                    "Symbol": w_sym, "Name": w_sym, "Kurs (EUR €)": "N/A", 
                    "Tagesveränderung (€)": "N/A", "Kurs (Original)": "N/A", 
                    "Tagesveränderung (Original)": "N/A", "Forward KGV": "N/A", "Branche": "N/A"
                })
        
        st.dataframe(pd.DataFrame(wl_data), use_container_width=True)
        
        col_wl1, col_wl2 = st.columns([1, 1])
        with col_wl1:
            remove_sym = st.selectbox("Aktie aus Watchlist entfernen:", st.session_state.watchlist)
            if st.button("❌ Ausgewählte Aktie entfernen", use_container_width=True):
                st.session_state.watchlist.remove(remove_sym)
                st.rerun()

        with col_wl2:
            wl_df = pd.DataFrame({"Symbol": st.session_state.watchlist})
            csv_data = wl_df.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Watchlist als CSV Exportieren", data=csv_data, file_name="watchlist.csv", mime="text/csv", use_container_width=True)
    else:
        st.info("Deine Watchlist ist aktuell leer.")

# ==========================================
# FENSTER 3: AKTIEN-SCREENER (MIT DAY-TRADING & EINSTIEGS-SIGNALEN)
# ==========================================
elif main_nav == "🔍 Aktien-Screener":
    st.markdown("## 🔍 Aktien-Screener & Tages-Einstiege")
    st.caption("Durchsuche Märkte nach fundamentaler Stärke und tagesaktuellen Trading-Signalen.")

    col_sel1, col_sel2 = st.columns([1, 2])
    with col_sel1:
        selected_preset = st.selectbox("Aktien-Gruppe:", list(SCREENER_LISTS.keys()))
        custom_symbols_input = st.text_area("Oder Symbole eingeben:", value=", ".join(SCREENER_LISTS[selected_preset]))
        
        signal_filter = st.multiselect(
            "Tages-Einstiegssignale filtern (optional):",
            ["🔥 Volumen-Ausbruch (> 1.5x Ø Vol)", "📈 20-Tage-Hoch Durchbruch", "📉 RSI Überverkauft (< 35)", "🎯 Nahe 200-SMA Support"],
            default=[]
        )

    with col_sel2:
        min_score = st.slider("Mindest-Score (0–5):", 0, 5, 2)
        max_pe = st.number_input("Maximales Forward KGV:", value=40.0, step=5.0)

    if st.button("🚀 Screening starten", use_container_width=True):
        symbols_to_scan = [s.strip().upper() for s in custom_symbols_input.split(",") if s.strip()]
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, sym in enumerate(symbols_to_scan):
            status_text.text(f"Analysiere {sym} ({idx+1}/{len(symbols_to_scan)})...")
            progress_bar.progress((idx + 1) / len(symbols_to_scan))
            time.sleep(0.4)

            try:
                t = yf.Ticker(sym)
                inf = t.info
                df_h = t.history(period="1y")

                if df_h.empty or len(df_h) < 50: 
                    continue

                f_pe = inf.get('forwardPE', 999)
                margin = (inf.get('profitMargins', 0) or 0) * 100
                roe_sc = (inf.get('returnOnEquity', 0) or 0) * 100
                price = inf.get('currentPrice', inf.get('regularMarketPrice', df_h['Close'].iloc[-1]))
                s_curr = inf.get('currency', 'USD').upper()
                s_rate = get_eur_exchange_rate(s_curr)

                df_h['SMA_50'] = ta.trend.sma_indicator(df_h['Close'], window=50)
                df_h['SMA_200'] = ta.trend.sma_indicator(df_h['Close'], window=200) if len(df_h) >= 200 else df_h['SMA_50']
                df_h['RSI'] = ta.momentum.rsi(df_h['Close'], window=14)
                df_h['Vol_SMA20'] = df_h['Volume'].rolling(20).mean()

                last_c = df_h['Close'].iloc[-1]
                last_s200 = df_h['SMA_200'].iloc[-1]
                last_r = df_h['RSI'].iloc[-1] if not pd.isna(df_h['RSI'].iloc[-1]) else 50
                last_vol = df_h['Volume'].iloc[-1]
                avg_vol = df_h['Vol_SMA20'].iloc[-1]
                high_20d = df_h['High'].iloc[-21:-1].max() if len(df_h) > 21 else df_h['High'].max()

                c_score = 0
                if last_c > last_s200: c_score += 1
                if last_r < 35: c_score += 1
                if f_pe < 25: c_score += 1
                if margin > 12: c_score += 1
                if roe_sc > 12: c_score += 1

                today_signals = []
                if avg_vol > 0 and (last_vol / avg_vol) >= 1.5:
                    today_signals.append("🔥 Vol-Spike")
                if last_c >= high_20d:
                    today_signals.append("📈 20D-Breakout")
                if last_r <= 35:
                    today_signals.append("📉 RSI Oversold")
                if last_s200 > 0 and abs(last_c - last_s200) / last_s200 <= 0.02:
                    today_signals.append("🎯 200-SMA Test")

                match_signal_filter = True
                if "🔥 Volumen-Ausbruch (> 1.5x Ø Vol)" in signal_filter and "🔥 Vol-Spike" not in today_signals:
                    match_signal_filter = False
                if "📈 20-Tage-Hoch Durchbruch" in signal_filter and "📈 20D-Breakout" not in today_signals:
                    match_signal_filter = False
                if "📉 RSI Überverkauft (< 35)" in signal_filter and "📉 RSI Oversold" not in today_signals:
                    match_signal_filter = False
                if "🎯 Nahe 200-SMA Support" in signal_filter and "🎯 200-SMA Test" not in today_signals:
                    match_signal_filter = False

                if c_score >= min_score and f_pe <= max_pe and match_signal_filter:
                    results.append({
                        "Symbol": sym,
                        "Name": inf.get('shortName', sym),
                        "Tages-Signal": ", ".join(today_signals) if today_signals else "➖ Konsolidierung",
                        "Score": f"{c_score} / 5",
                        "Kurs (Original)": f"{price:.2f} {s_curr}" if price else "N/A",
                        "Kurs (EUR €)": f"{price * s_rate:.2f} €" if price else "N/A",
                        "Volumen vs Ø": f"{(last_vol / avg_vol):.1f}x" if avg_vol > 0 else "N/A",
                        "Forward KGV": round(f_pe, 2) if f_pe != 999 else "N/A",
                        "RSI (14)": round(last_r, 1)
                    })
            except Exception: 
                continue

        status_text.empty()
        progress_bar.empty()

        if results:
            st.success(f"Gefunden: {len(results)} Aktien entsprechen deinen Kriterien!")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
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
            # 1. Indizes Daten abrufen
            sp500 = yf.Ticker("^GSPC").history(period="1y")
            vix = yf.Ticker("^VIX").history(period="1d")
            dax = yf.Ticker("^GDAXI").history(period="1y")

            last_sp500 = sp500['Close'].iloc[-1]
            sp500_sma200 = ta.trend.sma_indicator(sp500['Close'], window=200).iloc[-1]
            vix_level = vix['Close'].iloc[-1] if not vix.empty else 20.0
            sp500_rsi = ta.momentum.rsi(sp500['Close'], window=14).iloc[-1]

            # 2. Fear & Greed Index (0 - 100) berechnen
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

            # 3. Makro-Kacheln
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            with col_m1:
                st.metric("Fear & Greed Index", f"{fg_index} / 100", delta=fg_status)

            with col_m2:
                sp500_status = "🟢 Bullenmarkt (> 200-SMA)" if last_sp500 > sp500_sma200 else "🔴 Bärenmarkt (< 200-SMA)"
                st.metric("S&P 500 Haupttrend", f"{last_sp500:,.0f} Pkt.", delta=sp500_status)

            with col_m3:
                if vix_level < 15: vix_status = "🟢 Entspannt"
                elif vix_level < 25: vix_status = "🟡 Moderat"
                else: vix_status = "🔴 Panik"
                st.metric("VIX Volatilität", f"{vix_level:.1f}", delta=vix_status)

            with col_m4:
                last_dax = dax['Close'].iloc[-1]
                dax_sma200 = ta.trend.sma_indicator(dax['Close'], window=200).iloc[-1]
                dax_status = "🟢 Aufwärtstrend" if last_dax > dax_sma200 else "🔴 Abwärtstrend"
                st.metric("DAX Index", f"{last_dax:,.0f} Pkt.", delta=dax_status)

            st.markdown("<br>", unsafe_allow_html=True)

            # 4. Markt-Synthese & Ausblick
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

            # 5. Sektor-Rotations-Vergleich
            st.markdown("### 📊 Sektor-Rotation (Performance 1 Monat)")
            
            sector_data = []
            for name, ticker_sym in SECTOR_ETFS.items():
                try:
                    sec_hist = yf.Ticker(ticker_sym).history(period="1mo")
                    if not sec_hist.empty:
                        change_1m = ((sec_hist['Close'].iloc[-1] - sec_hist['Close'].iloc[0]) / sec_hist['Close'].iloc[0]) * 100
                        sector_data.append({"Sektor": name, "Performance (%)": change_1m})
                except Exception: pass

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
