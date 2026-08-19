import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import ta
from streamlit_searchbox import st_searchbox
from yahooquery import search

# Seiten-Konfiguration
st.set_page_config(page_title="Aktienanalyse & Valuation Tool", layout="wide")

# Vordefinierte Aktienlisten für den Screener
SCREENER_LISTS = {
    "US Big Tech & Growth": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "NFLX", "INTC"],
    "DAX 40 (Auswahl)": ["SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "MBG.DE", "BMW.DE", "VOW3.DE", "BAS.DE", "RHM.DE"],
    "S&P 500 Top Pick Mix": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "JNJ", "JPM", "V", "PG", "UNH", "HD", "MA", "DIS"]
}

st.title("📊 Professionelles Aktienanalyse- & Screener-Tool")

# ==========================================
# FUNKTION FÜR LIVE-SUCHVORSCHLÄGE
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
# SEITENLEISTE: LIVE-AKTIENSUCHE
# ==========================================
st.sidebar.header("🔍 Live-Aktiensuche")

selected_ticker = st_searchbox(
    search_companies,
    key="stock_search_box",
    placeholder="Name oder Symbol tippen (z.B. Microsoft, SAP)..."
)

ticker_symbol = selected_ticker.upper() if selected_ticker else "AAPL"

# ==========================================
# EINZELANALYSE (HAUPTBEREICH)
# ==========================================
if ticker_symbol:
    ticker = yf.Ticker(ticker_symbol)
    
    try:
        info = ticker.info
        
        # Header & Stammdaten
        st.header(f"{info.get('longName', ticker_symbol)} ({info.get('symbol', ticker_symbol)})")
        st.write(f"**Branche:** {info.get('industry', 'N/A')} | **Sektor:** {info.get('sector', 'N/A')} | **Währung:** {info.get('currency', 'USD')}")
        
        # 1. Daten für Kennzahlen und Indikatoren vorab berechnen
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        kgv = info.get('forwardPE', 'N/A')
        marge = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 'N/A'
        roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 'N/A'
        
        # Historie & Technische Indikatoren
        df_daily = ticker.history(period="1y")
        has_tech_data = not df_daily.empty and len(df_daily) >= 200
        
        if has_tech_data:
            df_daily['SMA_50'] = ta.trend.sma_indicator(df_daily['Close'], window=50)
            df_daily['SMA_200'] = ta.trend.sma_indicator(df_daily['Close'], window=200)
            df_daily['RSI'] = ta.momentum.rsi(df_daily['Close'], window=14)
            
            last_close = df_daily['Close'].iloc[-1]
            last_sma50 = df_daily['SMA_50'].iloc[-1]
            last_sma200 = df_daily['SMA_200'].iloc[-1]
            last_rsi = df_daily['RSI'].iloc[-1]
        else:
            last_close = current_price
            last_sma50 = last_sma200 = last_rsi = 0

        # DCF Vorberechnung für das Executive Banner
        cashflow_df = ticker.cashflow
        free_cash_flow = 0
        if not cashflow_df.empty and 'Free Cash Flow' in cashflow_df.index:
            free_cash_flow = cashflow_df.loc['Free Cash Flow'].iloc[0] / 1e6
        
        shares_outstanding = info.get('sharesOutstanding', 1) / 1e6
        total_debt = info.get('totalDebt', 0) / 1e6
        total_cash = info.get('totalCash', 0) / 1e6
        net_debt = total_debt - total_cash

        # Standard DCF-Schnellwert (9% WACC, 10% Wachstum 1-5, 5% 6-10, Exit 15)
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

        # Scoring Vorberechnung
        score = 0
        max_score = 6
        reasons = []

        if has_tech_data:
            if last_close > last_sma200:
                score += 1
                reasons.append(("🟢 Positiv", "Kurs liegt über dem SMA 200 (Übergeordneter Aufwärtstrend)"))
            else:
                reasons.append(("🔴 Negativ", "Kurs liegt unter dem SMA 200 (Übergeordneter Abwärtstrend)"))

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
        # EXECUTIVE SUMMARY BANNER (TOP-AUF EINEN BLICK)
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
            
        with banner_col3:
            if dcf_margin > 15:
                st.success(f"🟢 **DCF-Rabatt:** {dcf_margin:+.1f}%\n\nUnter fairerm Wert ({dcf_fair_value:.2f} $)")
            elif dcf_margin < -15:
                st.error(f"🔴 **DCF-Aufschlag:** {dcf_margin:+.1f}%\n\nÜber fairerm Wert ({dcf_fair_value:.2f} $)")
            else:
                st.info(f"🟡 **DCF-Fairness:** {dcf_margin:+.1f}%\n\nNahe am fairen Wert ({dcf_fair_value:.2f} $)")

        with banner_col4:
            if has_tech_data:
                if last_rsi < 35:
                    st.success(f"🟢 **RSI Momentum:** {last_rsi:.1f}\n\nStark überverkauft")
                elif last_rsi > 65:
                    st.error(f"🔴 **RSI Momentum:** {last_rsi:.1f}\n\nÜberhitzt/Überkauft")
                else:
                    st.info(f"🟡 **RSI Momentum:** {last_rsi:.1f}\n\nNeutrale Zone")
            else:
                st.write("N/A")

        st.markdown("---")

        # Key-Metrics Zeile
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Aktueller Kurs", f"{current_price:.2f} $" if isinstance(current_price, (int, float)) else "N/A")
        col2.metric("Forward KGV", f"{kgv:.2f}" if isinstance(kgv, (int, float)) else kgv)
        col3.metric("Nettomarge", f"{marge:.2f}%" if isinstance(marge, (int, float)) else marge)
        col4.metric("Eigenkapitalrendite (ROE)", f"{roe:.2f}%" if isinstance(roe, (int, float)) else roe)

        st.markdown("---")

        # Tab-Navigation
        tab_chart, tab_signals, tab_dcf, tab_screener, tab_finances = st.tabs([
            "📈 Kursverlauf", 
            "🚦 Kauf-Indikatoren & Lage", 
            "🧮 DCF-Bewertungsmodell", 
            "🔍 Aktien-Screener",
            "📑 Finanzen & Bilanz"
        ])

        # ==========================================
        # TAB 1: CHART
        # ==========================================
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
                st.warning("Keine Kursdaten für diesen Zeitraum verfügbar.")

        # ==========================================
        # TAB 2: KAUF-INDIKATOREN & LAGE-ANALYSE
        # ==========================================
        with tab_signals:
            st.subheader("🚦 ÜBRESICHTLICHE LAGE-ANALYSE")
            
            if has_tech_data:
                col_score_tab, col_details_tab = st.columns([1, 2])
                
                with col_score_tab:
                    st.markdown("### Signal-Status")
                    st.metric("Punkte-Ergebnis", f"{score} / {max_score}")
                    
                    if score >= 5:
                        st.success("🔥 **STARKES KAUFSIGNAL**\nSowohl fundamental als auch technisch sehr gut aufgestellt.")
                    elif score >= 3:
                        st.info("⚠️ **HALTEN / BEOBACHTEN**\nGemischte Signale. Auf die Watchlist setzen.")
                    else:
                        st.error("⛔ **KEIN KAUF / VORSICHT**\nDie Mehrheit der Indikatoren rät derzeit ab.")

                with col_details_tab:
                    st.markdown("### Detail-Auswertung aller Kriterien")
                    for status, text in reasons:
                        st.write(f"**{status}:** {text}")
            else:
                st.warning("Zu wenige historische Kursdaten für die Indikatoren-Analyse verfügbar.")

        # ==========================================
        # TAB 3: DCF RECHNER
        # ==========================================
        with tab_dcf:
            st.subheader("🧮 Interactive Discounted Cashflow (DCF) Modell")
            
            col_params, col_results = st.columns([1, 1])

            with col_params:
                st.markdown("### ⚙️ Annahmen anpassen")
                
                fcf_base = st.number_input(
                    "Start Free Cashflow (Mio. $):", 
                    value=float(free_cash_flow) if free_cash_flow != 0 else 1000.0,
                    step=100.0
                )
                
                growth_years_1_5 = st.slider("FCF-Wachstum Jahre 1–5 (%):", 0.0, 40.0, 10.0, 0.5) / 100
                growth_years_6_10 = st.slider("FCF-Wachstum Jahre 6–10 (%):", 0.0, 30.0, 5.0, 0.5) / 100
                wacc = st.slider("Abzinsungssatz / WACC (%):", 5.0, 20.0, 9.0, 0.5) / 100
                terminal_multiple = st.slider("Exit Multiple (Ende Jahr 10):", 5.0, 40.0, 15.0, 0.5)

            # Dynamische DCF-Berechnung
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

                st.metric(
                    label="Berechneter Fairer Wert pro Aktie", 
                    value=f"{fair_value_per_share:.2f} $",
                    delta=f"{diff_percent:+.1f}% ggü. aktuellem Kurs"
                )

                st.markdown("---")
                st.write(f"**Barwert Cashflows (Jahre 1–10):** {pv_fcf_sum:,.2f} Mio. $")
                st.write(f"**Barwert Endwert (Terminal Value):** {discounted_tv:,.2f} Mio. $")
                st.write(f"**Nettoverschuldung:** {net_debt:,.2f} Mio. $")
                
                if fair_value_per_share > current_price:
                    st.success("Die Aktie erscheint unterbewertet.")
                else:
                    st.warning("Die Aktie erscheint überbewertet.")

        # ==========================================
        # TAB 4: AKTIEN-SCREENER
        # ==========================================
        with tab_screener:
            st.subheader("🔍 Aktien-Screener: Universum nach Kennzahlen filtern")
            st.write("Wähle eine Liste aus oder gib eigene Symbole ein, um mehrere Aktien automatisch zu analysieren und zu vergleichen.")

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
                    status_text.text(f"Analysiere {sym} ({idx+1}/{len(symbols_to_scan)})...")
                    progress_bar.progress((idx + 1) / len(symbols_to_scan))

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
                    res_df = pd.DataFrame(results)
                    st.success(f"Gefunden: {len(results)} Aktien entsprechen deinen Kriterien!")
                    st.dataframe(res_df, use_container_width=True)
                else:
                    st.warning("Keine Aktien entsprechen allen gewählten Filterkriterien.")

        # ==========================================
        # TAB 5: FINANZEN & BILANZ
        # ==========================================
        with tab_finances:
            st.subheader("📑 Jahresabschlüsse & Bilanzen")
            t1, t2, t3 = st.tabs(["Gewinn- und Verlustrechnung", "Bilanz", "Cashflow-Rechnung"])
            
            with t1:
                st.dataframe(ticker.financials, use_container_width=True)
            with t2:
                st.dataframe(ticker.balance_sheet, use_container_width=True)
            with t3:
                st.dataframe(ticker.cashflow, use_container_width=True)

    except Exception as e:
        st.error(f"Fehler beim Laden der Daten für Symbol '{ticker_symbol}': {e}")
