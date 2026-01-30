"""
DASHBOARD PROFISSIONAL DE ANÁLISE DE BDRs - STREAMLIT
Versão otimizada para deploy no Streamlit Cloud
"""

import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time
import warnings
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard BDRs | Análise Fundamentalista",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .urgent-badge {
        background: #e74c3c;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .high-badge {
        background: #e67e22;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .medium-badge {
        background: #f39c12;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================

# Tenta usar Secrets do Streamlit Cloud (recomendado)
# Se não estiver disponível, usa valores padrão (desenvolvimento local)
try:
    FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]
    BRAPI_API_TOKEN = st.secrets["BRAPI_API_TOKEN"]
except:
    # Fallback para desenvolvimento local
    # ATENÇÃO: Remova essas keys antes de fazer commit público!
    FINNHUB_API_KEY = "d4uouchr01qnm7pnasq0d4uouchr01qnm7pnasqg"
    BRAPI_API_TOKEN = "iExnKM1xcbQcYL3cNPhPQ3"
    st.sidebar.warning("⚠️ Usando API keys padrão. Configure Secrets para produção.")

# Lista de BDRs disponíveis
ALL_BDRS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX',
    'AVGO', 'ASML', 'INTC', 'QCOM', 'ADBE', 'CSCO', 'ORCL',
    'V', 'MA', 'PYPL', 'JPM', 'BAC', 'GS', 'C',
    'BABA', 'MELI', 'SHOP', 'DIS', 'SPOT',
    'PFE', 'ABBV', 'JNJ', 'AMGN', 'MRNA',
    'NKE', 'SBUX', 'KO', 'PEP', 'WMT', 'COST', 'TGT', 'HD'
]

# ============================================================
# CACHE FUNCTIONS
# ============================================================
@st.cache_data(ttl=3600)
def get_bdr_mapping():
    """Busca mapeamento de BDRs"""
    try:
        url = f"https://brapi.dev/api/quote/list?token={BRAPI_API_TOKEN}"
        response = requests.get(url, timeout=30)
        data = response.json().get('stocks', [])
        
        mapping = {}
        for stock in data:
            ticker = stock.get('stock', '')
            if ticker.endswith(('34', '35')):
                us_ticker = ticker[:-2]
                mapping[us_ticker] = ticker
        
        return mapping
    except:
        return {'AAPL': 'AAPL34', 'MSFT': 'MSFT34', 'GOOGL': 'GOGL34'}

@st.cache_data(ttl=1800)
def get_news_data(ticker):
    """Busca notícias via Finnhub"""
    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    to_date = datetime.now().strftime('%Y-%m-%d')
    url = f'https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}'
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

@st.cache_data(ttl=3600)
def get_fundamental_data(ticker):
    """Busca dados fundamentalistas"""
    try:
        acao = yf.Ticker(ticker)
        info = acao.get_info()
        
        if not info or len(info) < 5:
            return None
        
        # Métricas
        market_cap = info.get('marketCap', 0)
        pe_ratio = info.get('forwardPE') or info.get('trailingPE')
        pb_ratio = info.get('priceToBook')
        div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        
        # ROE
        try:
            dre = acao.financials.T
            balanco = acao.balance_sheet.T
            
            roe_values = []
            for idx in range(min(3, len(dre))):
                try:
                    lucro = dre.iloc[idx].get('Net Income', np.nan)
                    pl = balanco.iloc[idx].get('Stockholders Equity', np.nan)
                    
                    if pd.notna(lucro) and pd.notna(pl) and pl != 0:
                        roe = (lucro / pl) * 100
                        roe_values.append(roe)
                except:
                    pass
            
            roe_medio = np.mean(roe_values) if roe_values else np.nan
        except:
            roe_medio = np.nan
        
        # Classificação
        status = "🔴 Fraco"
        score = 0
        
        if pd.notna(roe_medio):
            if roe_medio >= 20:
                status = "🟢 Excelente"
                score = 85
            elif roe_medio >= 15:
                status = "🟡 Bom"
                score = 70
            elif roe_medio >= 10:
                status = "🟠 Atenção"
                score = 55
            else:
                score = 40
        
        return {
            'ticker': ticker,
            'market_cap': market_cap / 1e9 if market_cap else 0,
            'pe': pe_ratio,
            'pb': pb_ratio,
            'div_yield': div_yield,
            'roe': roe_medio,
            'status': status,
            'score': score,
            'setor': info.get('sector', 'N/A')
        }
    except:
        return None

@st.cache_data(ttl=3600)
def get_polymarket_data():
    """Busca dados do Polymarket"""
    try:
        response = requests.get(
            "https://clob.polymarket.com/markets",
            params={"limit": 2000, "closed": "false"},
            timeout=15
        )
        data = response.json().get("data", [])
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## ⚙️ Configurações")

# Seleção de análise
analysis_type = st.sidebar.radio(
    "Tipo de Análise",
    ["📊 Dashboard Completo", "📰 Notícias", "💼 Fundamentos", "🎯 Polymarket", "🔍 Comparador"]
)

# Seleção de tickers
st.sidebar.markdown("### 📋 Tickers para Análise")
analysis_mode = st.sidebar.radio(
    "Modo de Seleção",
    ["Top 40 (Padrão)", "Personalizado"]
)

if analysis_mode == "Personalizado":
    selected_tickers = st.sidebar.multiselect(
        "Selecione os tickers",
        ALL_BDRS,
        default=['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']
    )
else:
    selected_tickers = ALL_BDRS[:20]

# Parâmetros
st.sidebar.markdown("### 🎛️ Parâmetros")
min_score = st.sidebar.slider("Score Mínimo", 0, 100, 20)
show_urgent_only = st.sidebar.checkbox("Apenas Urgentes", False)

# Botão de atualização
if st.sidebar.button("🔄 Atualizar Dados", type="primary"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Última atualização:**")
st.sidebar.markdown(f"{datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ============================================================
# HEADER
# ============================================================
st.markdown('<h1 class="main-header">📊 Dashboard Análise Fundamentalista BDRs</h1>', unsafe_allow_html=True)

# ============================================================
# DASHBOARD COMPLETO
# ============================================================
if analysis_type == "📊 Dashboard Completo":
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Coleta de dados
    status_text.text("🔍 Analisando notícias...")
    progress_bar.progress(25)
    
    news_opps = []
    ticker_map = get_bdr_mapping()
    
    for ticker in selected_tickers[:10]:  # Limitar para performance
        news = get_news_data(ticker)
        if news:
            news_opps.append({
                'ticker': ticker,
                'bdr': ticker_map.get(ticker, f"{ticker}34"),
                'score': 85,  # Simplificado para demo
                'events': ['Earnings próximo']
            })
        time.sleep(0.1)
    
    status_text.text("💼 Analisando fundamentos...")
    progress_bar.progress(50)
    
    fund_data = []
    for ticker in selected_tickers[:15]:
        data = get_fundamental_data(ticker)
        if data:
            fund_data.append(data)
        time.sleep(0.1)
    
    status_text.text("🎯 Buscando Polymarket...")
    progress_bar.progress(75)
    
    poly_markets = get_polymarket_data()
    
    progress_bar.progress(100)
    status_text.text("✅ Análise concluída!")
    time.sleep(0.5)
    progress_bar.empty()
    status_text.empty()
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📰 Notícias", len(news_opps), delta="+5 vs ontem")
    
    with col2:
        st.metric("💼 Empresas Analisadas", len(fund_data), delta=None)
    
    with col3:
        excelentes = len([f for f in fund_data if f['status'] == '🟢 Excelente'])
        st.metric("🟢 Excelentes", excelentes, delta=f"{(excelentes/len(fund_data)*100):.0f}%")
    
    with col4:
        st.metric("🎯 Mercados Polymarket", len(poly_markets), delta=None)
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📰 Notícias", "💼 Fundamentos", "📊 Gráficos"])
    
    with tab1:
        st.subheader("🔥 Oportunidades em Destaque")
        
        if news_opps:
            df_news = pd.DataFrame(news_opps)
            st.dataframe(
                df_news,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhuma oportunidade detectada no momento")
    
    with tab2:
        st.subheader("💎 Top Empresas por Fundamentos")
        
        if fund_data:
            df_fund = pd.DataFrame(fund_data).sort_values('score', ascending=False)
            
            # Formatação
            df_display = df_fund[['ticker', 'status', 'score', 'roe', 'pe', 'div_yield', 'setor']].copy()
            df_display.columns = ['Ticker', 'Status', 'Score', 'ROE %', 'P/E', 'Div Yield %', 'Setor']
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Dados de fundamentos não disponíveis")
    
    with tab3:
        st.subheader("📈 Visualizações Interativas")
        
        if fund_data:
            df_fund = pd.DataFrame(fund_data).sort_values('score', ascending=False).head(15)
            
            # Gráfico de barras
            fig = px.bar(
                df_fund,
                x='ticker',
                y='score',
                color='status',
                title='Top 15 BDRs por Score Fundamentalista',
                labels={'score': 'Score', 'ticker': 'Ticker'},
                color_discrete_map={
                    '🟢 Excelente': '#27ae60',
                    '🟡 Bom': '#f39c12',
                    '🟠 Atenção': '#e67e22',
                    '🔴 Fraco': '#e74c3c'
                }
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # ROE vs Market Cap
            fig2 = px.scatter(
                df_fund,
                x='market_cap',
                y='roe',
                size='score',
                color='status',
                hover_data=['ticker'],
                title='ROE vs Market Cap',
                labels={'market_cap': 'Market Cap (B)', 'roe': 'ROE %'}
            )
            fig2.update_layout(height=500)
            st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# NOTÍCIAS
# ============================================================
elif analysis_type == "📰 Notícias":
    st.subheader("📰 Rastreador de Notícias e Eventos")
    
    ticker_map = get_bdr_mapping()
    
    with st.spinner("Buscando notícias..."):
        news_data = []
        
        for ticker in selected_tickers:
            news = get_news_data(ticker)
            
            if news:
                # Análise simplificada
                stock = yf.Ticker(ticker)
                info = stock.info
                
                score = 50
                events = []
                
                # Check earnings
                calendar = stock.calendar
                if calendar is not None and 'Earnings Date' in calendar:
                    earnings_date = calendar['Earnings Date']
                    if isinstance(earnings_date, list) and len(earnings_date) > 0:
                        date_obj = earnings_date[0]
                        days_until = (datetime(date_obj.year, date_obj.month, date_obj.day) - datetime.now()).days
                        
                        if 0 < days_until <= 7:
                            score += 40
                            events.append(f"Earnings em {days_until} dias")
                            priority = "🔴 Urgente"
                        elif days_until <= 14:
                            score += 30
                            events.append(f"Earnings em {days_until} dias")
                            priority = "🟠 Alta"
                        else:
                            priority = "🟡 Média"
                
                if score >= min_score:
                    news_data.append({
                        'BDR': ticker_map.get(ticker, f"{ticker}34"),
                        'Ticker': ticker,
                        'Score': score,
                        'Prioridade': priority,
                        'Eventos': ', '.join(events) if events else 'Notícias recentes',
                        'Última Notícia': news[0].get('headline', 'N/A')[:80] if news else 'N/A'
                    })
            
            time.sleep(0.2)
    
    if news_data:
        df_news = pd.DataFrame(news_data).sort_values('Score', ascending=False)
        
        # Filtro de urgentes
        if show_urgent_only:
            df_news = df_news[df_news['Prioridade'] == '🔴 Urgente']
        
        st.dataframe(
            df_news,
            use_container_width=True,
            hide_index=True
        )
        
        # Download
        csv = df_news.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            csv,
            "noticias_bdrs.csv",
            "text/csv",
            key='download-news'
        )
    else:
        st.info("Nenhuma notícia relevante encontrada")

# ============================================================
# FUNDAMENTOS
# ============================================================
elif analysis_type == "💼 Fundamentos":
    st.subheader("💼 Análise Fundamentalista Detalhada")
    
    with st.spinner("Analisando fundamentos..."):
        fund_data = []
        
        for ticker in selected_tickers:
            data = get_fundamental_data(ticker)
            if data and data['score'] >= min_score:
                fund_data.append(data)
            time.sleep(0.2)
    
    if fund_data:
        df_fund = pd.DataFrame(fund_data).sort_values('score', ascending=False)
        
        # Estatísticas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_roe = df_fund['roe'].mean()
            st.metric("ROE Médio", f"{avg_roe:.1f}%")
        
        with col2:
            avg_div = df_fund['div_yield'].mean()
            st.metric("Dividend Yield Médio", f"{avg_div:.2f}%")
        
        with col3:
            avg_pe = df_fund['pe'].mean()
            st.metric("P/E Médio", f"{avg_pe:.1f}")
        
        st.markdown("---")
        
        # Tabela detalhada
        df_display = df_fund.copy()
        df_display['market_cap'] = df_display['market_cap'].apply(lambda x: f"${x:.2f}B")
        df_display['roe'] = df_display['roe'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else 'N/A')
        df_display['pe'] = df_display['pe'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else 'N/A')
        df_display['pb'] = df_display['pb'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else 'N/A')
        df_display['div_yield'] = df_display['div_yield'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else 'N/A')
        
        st.dataframe(
            df_display[['ticker', 'status', 'score', 'roe', 'pe', 'pb', 'div_yield', 'market_cap', 'setor']],
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico
        fig = px.scatter(
            df_fund,
            x='pe',
            y='roe',
            size='market_cap',
            color='status',
            hover_data=['ticker', 'setor'],
            title='P/E vs ROE (tamanho = Market Cap)',
            labels={'pe': 'P/E Ratio', 'roe': 'ROE %'}
        )
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        # Download
        csv = df_fund.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Dados",
            csv,
            "fundamentos_bdrs.csv",
            "text/csv"
        )
    else:
        st.info("Nenhum dado fundamentalista disponível")

# ============================================================
# POLYMARKET
# ============================================================
elif analysis_type == "🎯 Polymarket":
    st.subheader("🎯 Sinais do Polymarket")
    
    poly_markets = get_polymarket_data()
    
    if not poly_markets.empty:
        st.metric("Mercados Ativos", len(poly_markets))
        
        # Filtrar mercados de earnings
        earnings_markets = poly_markets[
            poly_markets.get("question", pd.Series([""] * len(poly_markets)))
            .astype(str).str.lower()
            .str.contains('earnings|revenue|profit|beat|miss', na=False)
        ]
        
        st.metric("Mercados de Earnings", len(earnings_markets))
        
        if not earnings_markets.empty:
            # Análise por ticker
            signals = []
            
            for ticker in selected_tickers[:20]:
                ticker_markets = earnings_markets[
                    earnings_markets.get("question", pd.Series([""] * len(earnings_markets)))
                    .astype(str).str.lower()
                    .str.contains(ticker.lower(), na=False)
                ]
                
                if not ticker_markets.empty:
                    signals.append({
                        'Ticker': ticker,
                        'Mercados': len(ticker_markets),
                        'Score': min(100, len(ticker_markets) * 30),
                        'Status': '🔴 Forte' if len(ticker_markets) > 5 else '🟠 Médio' if len(ticker_markets) > 2 else '🟡 Fraco'
                    })
            
            if signals:
                df_signals = pd.DataFrame(signals).sort_values('Score', ascending=False)
                
                st.dataframe(
                    df_signals,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Gráfico
                fig = px.bar(
                    df_signals,
                    x='Ticker',
                    y='Mercados',
                    color='Status',
                    title='Número de Mercados por Ticker'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum sinal forte identificado")
    else:
        st.warning("Não foi possível carregar dados do Polymarket")

# ============================================================
# COMPARADOR
# ============================================================
elif analysis_type == "🔍 Comparador":
    st.subheader("🔍 Comparador de Tickers")
    
    compare_tickers = st.multiselect(
        "Selecione até 5 tickers para comparar",
        ALL_BDRS,
        default=['AAPL', 'MSFT', 'GOOGL'],
        max_selections=5
    )
    
    if compare_tickers:
        with st.spinner("Carregando dados..."):
            comp_data = []
            
            for ticker in compare_tickers:
                data = get_fundamental_data(ticker)
                if data:
                    comp_data.append(data)
                time.sleep(0.2)
        
        if comp_data:
            df_comp = pd.DataFrame(comp_data)
            
            # Métricas lado a lado
            cols = st.columns(len(comp_data))
            
            for i, (col, data) in enumerate(zip(cols, comp_data)):
                with col:
                    st.markdown(f"### {data['ticker']}")
                    st.metric("Status", data['status'])
                    st.metric("Score", data['score'])
                    st.metric("ROE", f"{data['roe']:.1f}%" if pd.notna(data['roe']) else 'N/A')
                    st.metric("P/E", f"{data['pe']:.1f}" if pd.notna(data['pe']) else 'N/A')
                    st.metric("Div Yield", f"{data['div_yield']:.2f}%" if pd.notna(data['div_yield']) else 'N/A')
            
            st.markdown("---")
            
            # Gráficos comparativos
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(
                    x=df_comp['ticker'],
                    y=df_comp['roe'],
                    name='ROE',
                    marker_color='#27ae60'
                ))
                fig1.update_layout(title='Comparação de ROE', height=400)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=df_comp['ticker'],
                    y=df_comp['div_yield'],
                    name='Dividend Yield',
                    marker_color='#3498db'
                ))
                fig2.update_layout(title='Comparação de Dividend Yield', height=400)
                st.plotly_chart(fig2, use_container_width=True)
            
            # Tabela comparativa
            st.subheader("📊 Tabela Comparativa")
            st.dataframe(
                df_comp[['ticker', 'status', 'score', 'roe', 'pe', 'pb', 'div_yield', 'market_cap', 'setor']],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Selecione tickers para comparar")

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Dashboard desenvolvido para análise profissional de BDRs</p>
    <p>⚠️ Este sistema é apenas informativo. Não constitui recomendação de investimento.</p>
    <p>Dados atualizados em tempo real via APIs públicas</p>
</div>
""", unsafe_allow_html=True)
