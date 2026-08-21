import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import ta
import time
import io
import datetime
from streamlit_searchbox import st_searchbox
from yahooquery import search
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Seiten-Konfiguration
st.set_page_config(page_title="Aktienanalyse & Valuation Tool", layout="wide")

SCREENER_LISTS = {
    "US Big Tech & Growth": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "NFLX", "INTC"],
    "DAX 40 (Auswahl)": ["SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "MBG.DE", "BMW.DE", "VOW3.DE", "BAS.DE", "RHM.DE"],
    "S&P 500 Top Pick Mix": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "JNJ", "JPM", "V", "PG", "UNH", "HD", "MA", "DIS"]
}

# ==========================================
# CACHING-FUNKTION
# ==========================================
@st.cache_data(ttl=900, show_spinner=False)
def load_stock_data(symbol):
    ticker = yf.Ticker(symbol)
    info = ticker.info
    df_daily = ticker.history(period="1y")
    cashflow_df = ticker.cashflow
    financials_df = ticker.financials
    balance_sheet_df = ticker.balance_sheet
    
    # News & Kalender versuchen zu laden
    try:
        news_data = ticker.news
    except Exception:
        news_data = []
        
    try:
        calendar_data = ticker.calendar
    except Exception:
        calendar_data = None
        
    return info, df_daily, cashflow_df, financials_df, balance_sheet_df, news_data, calendar_data

# ==========================================
# LIVE-SUCHFUNKTION
# ==========================================
def search_companies(search_term: str):
    if not search_term or len(search_term) < 2:
        return []
    try:
        results = search(search_term)
        quotes = results.get('quotes', [])
        options = []
        for q in quotes:
            symbol = q.get('symbol')
            name = q.get('shortname', q.get('longname', symbol))
            exch = q.get('exchDisp', '')
            if symbol:
                label = f"{name} ({symbol}) - {exch}" if exch else f"{name} ({symbol})"
                options.append((label, symbol))
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
def generate_pdf_report(symbol, company_name, current_price, fair_value, score, piotroski_score, reasons):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1E1E1E"))
    story.append(Paragraph(f"Aktienanalyse-Report: {company_name} ({symbol})", title_style))
    story.append(Spacer(1, 12))

    data = [
        ["Metrik", "Wert"],
        ["Aktueller Kurs", f"{current_price:.2f} $"],
        ["DCF Fairer Wert", f"{fair_value:.2f} $"],
        ["Gesamt-Score", f"{score} / 6 Punkte"],
        ["Piotroski F-Score", f"{piotroski_score} / 5 Punkte"]
    ]
    
    t = Table(data, colWidths=[200, 200])
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

st.title("📊 Professionelles Aktienanalyse- & Screener-Tool")

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["AAPL", "MSFT", "NVDA", "SAP.DE"]

# ==========================================
# SEITENLEISTE
# ==========================================
st.sidebar.header("🔍 Live-Aktiensuche")

selected_ticker = st_searchbox(
    search_companies,
    key="stock_search_box",
    placeholder="Name oder Symbol tippen (z.B. Microsoft, SAP)..."
)

ticker_symbol = selected_ticker.upper() if selected_ticker else "AAPL"

st.sidebar.markdown("---")
st.sidebar.header("⭐ Watchlist Manager")
if st.sidebar.button(f"➕ {ticker_symbol} zur Watchlist"):
    if ticker_symbol not in st.session_state.watchlist:
        st.session_state.watchlist.append(ticker_symbol)
        st.sidebar.success(f"{ticker_symbol} hinzugefügt!")

if st.session_state.watchlist:
    wl_df = pd.DataFrame({"Symbol": st.session_state.watchlist})
    csv_data = wl_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("💾 Watchlist als CSV exportieren", data=csv_data, file_name="watchlist.csv", mime="text/csv")

# ==========================================
# HAUPTBEREICH
# ==========================================
if ticker_symbol:
    try:
        with st.spinner(f"Lade Finanzdaten, News & Termine für {ticker_symbol}..."):
            info, df_daily, cashflow_df, financials_df, balance_sheet_df, news_data, calendar_data = load_stock_data(ticker_symbol)
            ticker = yf.Ticker(ticker_symbol)

        company_name = info.get('longName', ticker_symbol)
        st.header(f"{company_name} ({info.get('symbol', ticker_symbol)})")
        st.write(f"**Branche:** {info.get('industry', 'N/A')} | **Sektor:** {info.get('sector', 'N/A')} | **Währung:** {info.get('currency', 'USD')}")
        
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        kgv = info.get('forwardPE', 'N/A')
        marge = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 'N/A'
        roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 'N/A'
        
        has_tech_data = not df_daily.empty and len(df_daily) >= 200
        
        if has_tech_data:
            df_daily['SMA_50'] = ta.trend.sma_indicator(df_daily['Close'], window=50)
            df_daily['SMA_200'] = ta.trend.sma_indicator(df_daily['Close'], window=200)
            df_daily['RSI'] = ta.momentum.rsi(df_daily['Close'], window=14)
            
            last_close = df_daily['Close'].iloc[-1]
            last_sma50 = df_daily['SMA_50'].iloc[-1]
            last_sma200 = df_daily['SMA_200'].iloc[-1]
            last_rsi = df_daily['RSI'].iloc[-1]
            
            # Einstiegszonen Berechnung
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

        # Piotroski Berechnung
        piotroski_score, piotroski_details = calculate_piotroski_score(financials_df, balance_sheet_df, cashflow_df)

        # Scoring System
        score = 0
        max_score = 6
        reasons = []

        if has_tech_data:
            if last_close > last_sma200:
                score += 1
                reasons.append(("🟢 Positiv", "Kurs liegt über dem SMA 200 (Aufwärtstrend)"))
            else:
                reasons.append(("🔴 Negativ", "Kurs liegt unter dem SMA 200 (Abwärtstrend)"))

            if last_rsi < 35:
                score += 1
                reasons.append(("🟢 Positiv", f"RSI bei {last_rsi:.1f} (Überverkauft - Kaufchance)"))
            elif last_rsi > 65:
                reasons.append(("🔴 Negativ", f"RSI bei {last_rsi:.1f} (Überkauft - Rückschlagrisiko)"))
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
            reasons.append(("🔴 Negativ", "Geringe oder negative Nettomarge (< 15%)"))

        roe_val = info.get('returnOnEquity', 0)
        if roe_val and roe_val > 0.15:
            score += 1
            reasons.append(("🟢 Positiv", f"Hohe Eigenkapitalrendite ({roe_val*100:.1f}%)"))
        else:
            reasons.append(("🔴 Negativ", "Schwache Eigenkapitalrendite (< 15%)"))

        # ==========================================
        # EXECUTIVE SUMMARY BANNER
        # ==========================================
        st.markdown("### 🎯 Kaufgelegenheit auf einen Blick")
        
        banner_col1, banner_col2, banner_col3, banner_col4 = st.columns(4)
        
        with banner_col1:
            if score >= 5:
                st.success("🔥 **Gesamt-Urteil**\n\n**STARKES KAUFSIGNAL**")
            elif score >= 3:
                st.info("⚠️ **Gesamt-Urteil**\n\n**HALTEN / WATCHLIST**")
            else:
                st.error("⛔ **Gesamt-Urteil**\n\n**MEIDEN / ABWARTEN**")
                
        with banner_col2:
            st.metric("Gesamt-Score", f"{score} / {max_score} Pkt.")
            st.caption(f"Piotroski F-Score: **{piotroski_score} / 5**")
            
        with banner_col3:
            if dcf_margin > 15:
                st.success(f"🟢 **DCF-Rabatt:** {dcf_margin:+.1f}%\n\nUnter fairerm Wert ({dcf_fair_value:.2f} $)")
            elif dcf_margin < -15:
                st.error(f"🔴 **DCF-Aufschlag:** {dcf_margin:+.1f}%\n\nÜber fairerm Wert ({dcf_fair_value:.2f} $)")
            else:
                st.info(f"🟡 **DCF-Fairness:** {dcf_margin:+.1f}%\n\nNahe am fairen Wert ({dcf_fair_value:.2f} $)")

        with banner_col4:
            pdf_bytes = generate_pdf_report(ticker_symbol, company_name, current_price, dcf_fair_value, score, piotroski_score, reasons)
            st.download_button("📄 PDF-Report Herunterladen", data=pdf_bytes, file_name=f"{ticker_symbol}_Analyse.pdf", mime="application/pdf")

        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Aktueller Kurs", f"{current_price:.2f} $" if isinstance(current_price, (int, float)) else "N/A")
        col2.metric("Forward KGV", f"{kgv:.2f}" if isinstance(kgv, (int, float)) else kgv)
        col3.metric("Nettomarge", f"{marge:.2f}%" if isinstance(marge, (int, float)) else marge)
        col4.metric("Eigenkapitalrendite (ROE)", f"{roe:.2f}%" if isinstance(roe, (int, float)) else roe)

        st.markdown("---")

        # Tabs Navigation
        tab_chart, tab_entry, tab_news, tab_signals, tab_dcf, tab_screener, tab_watchlist, tab_finances = st.tabs([
            "📈 Kursverlauf", 
            "🎯 Einstiegszonen",
            "📰 News & Termine",
            "🚦 Kauf-Indikatoren & Lage", 
            "🧮 DCF-Bewertungsmodell", 
            "🔍 Aktien-Screener",
            "⭐ Meine Watchlist",
            "📑 Finanzen & Bilanz"
        ])

        # TAB 1: CHART
        with tab_chart:
            st.subheader("Kursverlauf & Kerzen-Chart")
            timeframe = st.selectbox("Zeitraum auswählen:", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
            hist = ticker.history(period=timeframe)

            if not hist.empty:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=hist.index,
                    open=hist['Open'],
                    high=hist['High'],
                    low=hist['Low'],
                    close=hist['Close'],
                    name="Kurs"
                ))
                fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Keine Kursdaten verfügbar.")

        # TAB 2: NEU - EINSTIEGSZONEN
        with tab_entry:
            st.subheader("🎯 Technische Einstiegszonen & Support-Szenarien")
            
            if has_tech_data:
                ez_col1, ez_col2 = st.columns([1, 1])
                
                with ez_col1:
                    st.markdown("#### 🛒 Einstiegs-Levels auf einen Blick")
                    st.info(f"**Aktueller Kurs:** {current_price:.2f} $")
                    st.success(f"**🟢 Ideale Kaufzone (Support / 200-SMA):** {entry_ideal_low:.2f} $ – {entry_ideal_high:.2f} $")
                    st.warning(f"**🟡 52-Wochen-Tief (Starker Support):** {low_52:.2f} $")
                    st.error(f"**🔴 52-Wochen-Hoch (Widerstand):** {high_52:.2f} $")

                    if current_price <= entry_ideal_high:
                        st.balloons()
                        st.success("🎯 **HINWEIS:** Die Aktie befindet sich derzeit in oder nahe der berechneten **Idealen Kaufzone**!")
                    else:
                        diff_to_entry = ((current_price - entry_ideal_high) / entry_ideal_high) * 100
                        st.info(f"Der aktuelle Kurs liegt noch **{diff_to_entry:.1f}%** über der idealen Kaufszone.")

                with ez_col2:
                    st.markdown("#### 📉 Kurskorridor im Chart")
                    fig_entry = go.Figure()
                    fig_entry.add_trace(go.Scatter(x=df_daily.index, y=df_daily['Close'], mode='lines', name='Kurs'))
                    fig_entry.add_trace(go.Scatter(x=df_daily.index, y=df_daily['SMA_200'], mode='lines', name='200-SMA', line=dict(dash='dash', color='orange')))
                    fig_entry.add_hrect(y0=entry_ideal_low, y1=entry_ideal_high, fillcolor="green", opacity=0.2, line_width=0, annotation_text="Ideale Kaufzone")
                    fig_entry.update_layout(template="plotly_dark", height=350)
                    st.plotly_chart(fig_entry, use_container_width=True)
            else:
                st.warning("Keine ausreichenden Kursdaten für Einstiegszonen verfügbar.")

        # TAB 3: NEU - NEWS & TERMINE
        with tab_news:
            st.subheader("📰 Wichtige Neuigkeiten & Unternehmens-Termine")
            
            col_news, col_cal = st.columns([2, 1])
            
            with col_news:
                st.markdown("#### 📰 Aktuelle Nachrichten")
                if news_data:
                    for item in news_data[:6]:
                        # Formatierung je nach YFinance News Struktur
                        content = item.get('content', {})
                        title = content.get('title', item.get('title', 'Kein Titel'))
                        provider = content.get('provider', {}).get('displayName', item.get('publisher', 'Nachrichtenquelle'))
                        pub_time = content.get('pubDate', item.get('providerPublishTime', ''))
                        
                        # Link
                        click_url = content.get('canonicalUrl', {}).get('url', item.get('link', '#'))

                        st.markdown(f"**[{title}]({click_url})**")
                        st.caption(f"Quelle: {provider} | Datum: {pub_time}")
                        st.markdown("---")
                else:
                    st.info("Keine aktuellen Nachrichten verfügbar.")

            with col_cal:
                st.markdown("#### 📅 Anstehende Termine & Zahlen")
                if calendar_data is not None and len(calendar_data) > 0:
                    st.json(calendar_data)
                else:
                    # Alternative: Earnings Dates versuchen abzurufen
                    try:
                        ed = ticker.get_earnings_dates(limit=4)
                        if ed is not None and not ed.empty:
                            st.write("**Nächste Quartalszahlen (Earnings):**")
                            st.dataframe(ed)
                        else:
                            st.info("Keine bevorstehenden Termine eingetragen.")
                    except Exception:
                        st.info("Keine Termine verfügbar.")

        # TAB 4: LAGE-ANALYSE
        with tab_signals:
            st.subheader("🚦 ÜBERSICHTLICHE LAGE-ANALYSE")
            col_score_tab, col_details_tab = st.columns([1, 2])
            
            with col_score_tab:
                st.markdown("### Gesamt-Ergebnis")
                st.metric("Punkte-Ergebnis", f"{score} / {max_score}")
                st.metric("Piotroski Bilanz-Score", f"{piotroski_score} / 5")
                
                if score >= 5:
                    st.success("🔥 **STARKES KAUFSIGNAL**\nFundamental und technisch top.")
                elif score >= 3:
                    st.info("⚠️ **HALTEN / BEOBACHTEN**\nGemischte Signale.")
                else:
                    st.error("⛔ **KEIN KAUF / VORSICHT**\nMeiden.")

            with col_details_tab:
                st.markdown("### Detail-Auswertung (Technik & Bewertung)")
                for status, text in reasons:
                    st.write(f"**{status}:** {text}")
                
                st.markdown("---")
                st.markdown("### Piotroski F-Score (Bilanzqualität)")
                for status, text in piotroski_details:
                    st.write(f"**{status}:** {text}")

        # TAB 5: DCF RECHNER
        with tab_dcf:
            st.subheader("🧮 Interactive Discounted Cashflow (DCF) Modell")
            col_params, col_results = st.columns([1, 1])

            with col_params:
                st.markdown("### ⚙️ Annahmen anpassen")
                fcf_base = st.number_input("Start Free Cashflow (Mio. $):", value=float(free_cash_flow) if free_cash_flow != 0 else 1000.0, step=100.0)
                growth_years_1_5 = st.slider("FCF-Wachstum Jahre 1–5 (%):", 0.0, 40.0, 10.0, 0.5) / 100
                growth_years_6_10 = st.slider("FCF-Wachstum Jahre 6–10 (%):", 0.0, 30.0, 5.0, 0.5) / 100
                wacc = st.slider("Abzinsungssatz / WACC (%):", 5.0, 20.0, 9.0, 0.5) / 100
                terminal_multiple = st.slider("Exit Multiple (Ende Jahr 10):", 5.0, 40.0, 15.0, 0.5)

            projected_fcf = []
            discounted_fcf = []
            current_fcf = fcf_base

            for year in range(1, 11):
                rate = growth_years_1_5 if year <= 5 else growth_years_6_10
                current_fcf = current_fcf * (1 + rate)
                disc_fcf = current_fcf / ((1 + wacc) ** year)
                projected_fcf.append(current_fcf)
                discounted_fcf.append(disc_fcf)

            terminal_value = projected_fcf[-1] * terminal_multiple
            discounted_tv = terminal_value / ((1 + wacc) ** 10)
            pv_fcf_sum = sum(discounted_fcf)
            enterprise_value = pv_fcf_sum + discounted_tv
            equity_value = enterprise_value - net_debt
            fair_value_per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0

            with col_results:
                st.markdown("### 🎯 Ergebnis")
                diff_percent = ((fair_value_per_share - current_price) / current_price) * 100 if current_price else 0

                st.metric(label="Berechneter Fairer Wert pro Aktie", value=f"{fair_value_per_share:.2f} $", delta=f"{diff_percent:+.1f}% ggü. aktuellem Kurs")
                st.markdown("---")
                st.write(f"**Barwert Cashflows (Jahre 1–10):** {pv_fcf_sum:,.2f} Mio. $")
                st.write(f"**Barwert Endwert (Terminal Value):** {discounted_tv:,.2f} Mio. $")
                st.write(f"**Nettoverschuldung:** {net_debt:,.2f} Mio. $")

        # TAB 6: SCREENER
        with tab_screener:
            st.subheader("🔍 Aktien-Screener: Universum nach Kennzahlen filtern")
            col_sel1, col_sel2 = st.columns([1, 2])
            
            with col_sel1:
                selected_preset = st.selectbox("Aktien-Gruppe auswählen:", list(SCREENER_LISTS.keys()))
                custom_symbols_input = st.text_area("Oder eigene Symbole eingeben (kommagetrennt):", value=", ".join(SCREENER_LISTS[selected_preset]))

            with col_sel2:
                st.markdown("#### 🎯 Filter-Kriterien")
                min_score = st.slider("Mindest-Score (Kauf-Indikatoren 0–5):", 0, 5, 3)
                max_pe = st.number_input("Maximales Forward KGV:", value=30.0, step=5.0)
                min_margin = st.slider("Mindest-Nettomarge (%):", 0.0, 50.0, 10.0, 1.0)

            if st.button("🚀 Screening starten"):
                symbols_to_scan = [s.strip().upper() for s in custom_symbols_input.split(",") if s.strip()]
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for idx, sym in enumerate(symbols_to_scan):
                    status_text.text(f"Analysiere {sym} ({idx+1}/{len(symbols_to_scan)})... Bitte warten.")
                    progress_bar.progress((idx + 1) / len(symbols_to_scan))
                    time.sleep(0.6)

                    try:
                        t = yf.Ticker(sym)
                        inf = t.info
                        df_h = t.history(period="1y")

                        if df_h.empty or len(df_h) < 200:
                            continue

                        f_pe = inf.get('forwardPE', 999)
                        margin = (inf.get('profitMargins', 0) or 0) * 100
                        roe_sc = (inf.get('returnOnEquity', 0) or 0) * 100
                        price = inf.get('currentPrice', inf.get('regularMarketPrice', 0))

                        df_h['SMA_200'] = ta.trend.sma_indicator(df_h['Close'], window=200)
                        df_h['RSI'] = ta.momentum.rsi(df_h['Close'], window=14)

                        last_c = df_h['Close'].iloc[-1]
                        last_s200 = df_h['SMA_200'].iloc[-1]
                        last_r = df_h['RSI'].iloc[-1]

                        c_score = 0
                        if last_c > last_s200: c_score += 1
                        if last_r < 35: c_score += 1
                        if f_pe < 20: c_score += 1
                        if margin > 15: c_score += 1
                        if roe_sc > 15: c_score += 1

                        if c_score >= min_score and f_pe <= max_pe and margin >= min_margin:
                            results.append({
                                "Symbol": sym,
                                "Name": inf.get('shortName', sym),
                                "Score": f"{c_score} / 5",
                                "Kurs ($)": round(price, 2) if price else "N/A",
                                "Forward KGV": round(f_pe, 2) if f_pe != 999 else "N/A",
                                "Nettomarge (%)": f"{margin:.1f}%",
                                "ROE (%)": f"{roe_sc:.1f}%",
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
                    st.warning("Keine Aktien entsprechen allen gewählten Filterkriterien.")

        # TAB 7: WATCHLIST BEREICH
        with tab_watchlist:
            st.subheader("⭐ Meine abgespeicherten Favoriten")
            if st.session_state.watchlist:
                wl_data = []
                for w_sym in st.session_state.watchlist:
                    try:
                        w_t = yf.Ticker(w_sym)
                        w_inf = w_t.info
                        wl_data.append({
                            "Symbol": w_sym,
                            "Name": w_inf.get('shortName', w_sym),
                            "Kurs ($)": w_inf.get('currentPrice', w_inf.get('regularMarketPrice', 'N/A')),
                            "Forward KGV": w_inf.get('forwardPE', 'N/A'),
                            "Branche": w_inf.get('industry', 'N/A')
                        })
                    except Exception:
                        continue
                
                wl_display_df = pd.DataFrame(wl_data)
                st.dataframe(wl_display_df, use_container_width=True)
                
                if st.button("🗑️ Watchlist leeren"):
                    st.session_state.watchlist = []
                    st.experimental_rerun()
            else:
                st.info("Deine Watchlist ist aktuell leer.")

        # TAB 8: FINANZEN
        with tab_finances:
            st.subheader("📑 Jahresabschlüsse & Bilanzen")
            t1, t2, t3 = st.tabs(["Gewinn- und Verlustrechnung", "Bilanz", "Cashflow-Rechnung"])
            with t1: st.dataframe(financials_df, use_container_width=True)
            with t2: st.dataframe(balance_sheet_df, use_container_width=True)
            with t3: st.dataframe(cashflow_df, use_container_width=True)

    except Exception as e:
        if "Too Many Requests" in str(e) or "Rate limited" in str(e):
            st.error("⚠️ **Yahoo Finance hat Anfragen vorübergehend gedrosselt (Rate Limit).**\n\nBitte warte 2–5 Minuten und lade die Seite neu.")
        else:
            st.error(f"Fehler beim Laden der Daten für '{ticker_symbol}': {e}")
