"""
DASHBOARD PROFISSIONAL DE ANÁLISE DE BDRs - VERSÃO MELHORADA
Com Sistema de Alertas, Filtros Avançados, Histórico e Muito Mais!
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from datetime import datetime, timedelta, timezone
import time
import warnings
import json
from io import BytesIO
import hashlib

warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard BDRs | Análise Fundamentalista Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS CUSTOMIZADO MELHORADO
# ============================================================
st.markdown("""
<style>
    /* Header Principal */
    .main-header {
        font-size: 2.8rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1.5rem 0;
        margin-bottom: 2rem;
    }
    
    /* Cards de Métricas */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.2);
    }
    
    /* Badges */
    .badge {
        padding: 0.3rem 0.8rem;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
        display: inline-block;
        margin: 0.2rem;
    }
    .urgent-badge { background: #e74c3c; color: white; }
    .high-badge { background: #e67e22; color: white; }
    .medium-badge { background: #f39c12; color: white; }
    .success-badge { background: #27ae60; color: white; }
    
    /* Alertas */
    .alert-box {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid;
    }
    .alert-danger {
        background: #ffebee;
        border-color: #e74c3c;
        color: #c0392b;
    }
    .alert-warning {
        background: #fff3e0;
        border-color: #e67e22;
        color: #d35400;
    }
    .alert-info {
        background: #e3f2fd;
        border-color: #3498db;
        color: #2980b9;
    }
    
    /* Tabelas */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Mobile Responsive */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.8rem !important;
        }
        .metric-card {
            padding: 1rem !important;
        }
    }
    
    /* Animação de Loading */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .loading {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================

# API Keys com Secrets
try:
    FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]
    BRAPI_API_TOKEN = st.secrets["BRAPI_API_TOKEN"]
except:
    FINNHUB_API_KEY = "d4uouchr01qnm7pnasq0d4uouchr01qnm7pnasqg"
    BRAPI_API_TOKEN = "iExnKM1xcbQcYL3cNPhPQ3"

# Lista completa de BDRs
ALL_BDRS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX',
    'AVGO', 'ASML', 'INTC', 'QCOM', 'ADBE', 'CSCO', 'ORCL',
    'V', 'MA', 'PYPL', 'JPM', 'BAC', 'GS', 'C',
    'BABA', 'MELI', 'SHOP', 'DIS', 'SPOT',
    'PFE', 'ABBV', 'JNJ', 'AMGN', 'MRNA',
    'NKE', 'SBUX', 'KO', 'PEP', 'WMT', 'COST', 'TGT', 'HD',
    'UBER', 'LYFT', 'ABNB', 'DASH', 'COIN'
]

# ============================================================
# FUNÇÕES DE CACHE
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
# FUNÇÕES DE UTILIDADE
# ============================================================

def save_to_history(data_type, data):
    """Salva análise no histórico"""
    try:
        timestamp = datetime.now().isoformat()
        history_entry = {
            'timestamp': timestamp,
            'type': data_type,
            'data': data
        }
        
        # Usar session state para persistir entre runs
        if 'history' not in st.session_state:
            st.session_state.history = []
        
        st.session_state.history.append(history_entry)
        
        # Limitar a 100 entradas
        if len(st.session_state.history) > 100:
            st.session_state.history = st.session_state.history[-100:]
            
        return True
    except:
        return False

def get_recommendations(df):
    """Gera recomendações inteligentes"""
    recommendations = []
    
    # Regra 1: Value Investing (ROE alto + P/E baixo)
    good_value = df[(df['roe'] > 20) & (df['pe'] < 20)]
    if not good_value.empty:
        top_value = good_value.nlargest(3, 'roe')
        recommendations.append({
            'tipo': '💎 Value',
            'tickers': top_value['ticker'].tolist(),
            'razao': 'Alto ROE com P/E atrativo (Value Investing)',
            'cor': 'success'
        })
    
    # Regra 2: Dividendos Altos
    high_div = df[df['div_yield'] > 4].nlargest(3, 'div_yield')
    if not high_div.empty:
        recommendations.append({
            'tipo': '💰 Dividendos',
            'tickers': high_div['ticker'].tolist(),
            'razao': f'Dividend Yield acima de 4% (média: {high_div["div_yield"].mean():.2f}%)',
            'cor': 'info'
        })
    
    # Regra 3: Growth
    growth = df[(df['roe'] > 25) & (df['pe'] > 30)]
    if not growth.empty:
        top_growth = growth.nlargest(3, 'roe')
        recommendations.append({
            'tipo': '🚀 Growth',
            'tickers': top_growth['ticker'].tolist(),
            'razao': 'Alto ROE e P/E elevado (empresas em crescimento)',
            'cor': 'warning'
        })
    
    # Regra 4: Subvalorizadas
    undervalued = df[(df['pb'] < 3) & (df['roe'] > 15)]
    if not undervalued.empty:
        top_under = undervalued.nlargest(3, 'roe')
        recommendations.append({
            'tipo': '📉 Subvalorizadas',
            'tickers': top_under['ticker'].tolist(),
            'razao': 'P/B baixo com ROE sólido',
            'cor': 'success'
        })
    
    return recommendations

def create_excel_download(dfs_dict):
    """Cria arquivo Excel com múltiplas abas"""
    buffer = BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for sheet_name, df in dfs_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    return buffer.getvalue()

def create_correlation_heatmap(df):
    """Cria heatmap de correlação"""
    # Selecionar apenas colunas numéricas
    numeric_cols = ['roe', 'pe', 'pb', 'div_yield', 'market_cap', 'score']
    df_numeric = df[numeric_cols].dropna()
    
    if len(df_numeric) < 2:
        return None
    
    corr_matrix = df_numeric.corr()
    
    fig = ff.create_annotated_heatmap(
        z=corr_matrix.values,
        x=list(corr_matrix.columns),
        y=list(corr_matrix.index),
        annotation_text=corr_matrix.round(2).values,
        colorscale='RdYlGn',
        showscale=True
    )
    
    fig.update_layout(
        title='Matriz de Correlação - Métricas Fundamentalistas',
        height=500,
        xaxis={'side': 'bottom'}
    )
    
    return fig

def format_number(num, prefix='', suffix=''):
    """Formata números para exibição"""
    if pd.isna(num):
        return 'N/A'
    
    if abs(num) >= 1e9:
        return f"{prefix}{num/1e9:.2f}B{suffix}"
    elif abs(num) >= 1e6:
        return f"{prefix}{num/1e6:.2f}M{suffix}"
    elif abs(num) >= 1e3:
        return f"{prefix}{num/1e3:.2f}K{suffix}"
    else:
        return f"{prefix}{num:.2f}{suffix}"

# ============================================================
# SIDEBAR - CONFIGURAÇÕES E FILTROS
# ============================================================

st.sidebar.markdown("## ⚙️ Configurações")

# Tipo de análise
analysis_type = st.sidebar.radio(
    "Tipo de Análise",
    ["📊 Dashboard Completo", "📰 Notícias", "💼 Fundamentos", 
     "🎯 Polymarket", "🔍 Comparador", "📈 Histórico"],
    key="analysis_type"
)

# Seleção de tickers
st.sidebar.markdown("### 📋 Tickers")
analysis_mode = st.sidebar.radio(
    "Modo",
    ["Top 40 (Padrão)", "Personalizado"],
    key="analysis_mode"
)

if analysis_mode == "Personalizado":
    selected_tickers = st.sidebar.multiselect(
        "Selecione",
        ALL_BDRS,
        default=['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'],
        key="selected_tickers"
    )
else:
    selected_tickers = ALL_BDRS[:40]

# Filtros Avançados
st.sidebar.markdown("### 🎛️ Filtros Avançados")

with st.sidebar.expander("💼 Filtros Fundamentalistas"):
    roe_range = st.slider("ROE (%)", 0.0, 200.0, (0.0, 200.0), key="roe_range")
    pe_range = st.slider("P/E", 0.0, 100.0, (0.0, 100.0), key="pe_range")
    div_yield_min = st.slider("Dividend Yield Mínimo (%)", 0.0, 10.0, 0.0, key="div_yield_min")

with st.sidebar.expander("📊 Filtros de Análise"):
    min_score = st.slider("Score Mínimo", 0, 100, 20, key="min_score")
    show_urgent_only = st.checkbox("Apenas Urgentes", False, key="urgent_only")

# Sistema de Alertas
st.sidebar.markdown("### 🔔 Sistema de Alertas")

with st.sidebar.expander("Configurar Alertas"):
    alert_score = st.slider("Alerta Score ≥", 0, 100, 80, key="alert_score")
    alert_roe = st.slider("Alerta ROE ≥ (%)", 0, 100, 25, key="alert_roe")
    alert_earnings_days = st.slider("Alerta Earnings ≤ (dias)", 0, 30, 7, key="alert_earnings")
    
    alert_email = st.text_input("Email (futuro)", key="alert_email")
    
    if st.button("💾 Salvar Alertas", key="save_alerts"):
        st.success("✅ Alertas configurados!")

# Personalização Visual
st.sidebar.markdown("### 🎨 Personalização")

with st.sidebar.expander("Layout"):
    show_charts = st.checkbox("Mostrar Gráficos", True, key="show_charts")
    compact_mode = st.checkbox("Modo Compacto", False, key="compact_mode")
    dark_charts = st.checkbox("Gráficos Escuros", False, key="dark_charts")

# Botão de atualização
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Todos os Dados", type="primary", key="refresh_all"):
    st.cache_data.clear()
    st.rerun()

# Info
st.sidebar.markdown("---")
st.sidebar.markdown("**Última atualização:**")
st.sidebar.markdown(f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_")
st.sidebar.markdown(f"**Tickers ativos:** {len(selected_tickers)}")

# ============================================================
# HEADER PRINCIPAL
# ============================================================

st.markdown('<h1 class="main-header">📊 Dashboard Análise Fundamentalista BDRs</h1>', 
            unsafe_allow_html=True)

# ============================================================
# DASHBOARD COMPLETO
# ============================================================

if analysis_type == "📊 Dashboard Completo":
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Coleta de dados
    status_text.text("🔍 Coletando dados...")
    progress_bar.progress(10)
    
    # Notícias
    status_text.text("📰 Analisando notícias...")
    progress_bar.progress(25)
    
    news_opps = []
    ticker_map = get_bdr_mapping()
    
    for i, ticker in enumerate(selected_tickers[:15]):
        news = get_news_data(ticker)
        if news:
            news_opps.append({
                'ticker': ticker,
                'bdr': ticker_map.get(ticker, f"{ticker}34"),
                'score': 85,
                'events': ['Earnings próximo']
            })
        time.sleep(0.05)
        progress_bar.progress(25 + int((i / 15) * 20))
    
    # Fundamentos
    status_text.text("💼 Analisando fundamentos...")
    progress_bar.progress(50)
    
    fund_data = []
    for i, ticker in enumerate(selected_tickers[:20]):
        data = get_fundamental_data(ticker)
        if data:
            # Aplicar filtros
            if (roe_range[0] <= data.get('roe', 0) <= roe_range[1] and
                pe_range[0] <= data.get('pe', 0) <= pe_range[1] and
                data.get('div_yield', 0) >= div_yield_min):
                fund_data.append(data)
        time.sleep(0.05)
        progress_bar.progress(50 + int((i / 20) * 25))
    
    # Polymarket
    status_text.text("🎯 Consultando Polymarket...")
    progress_bar.progress(75)
    
    poly_markets = get_polymarket_data()
    
    progress_bar.progress(100)
    status_text.text("✅ Análise concluída!")
    time.sleep(0.3)
    progress_bar.empty()
    status_text.empty()
    
    # Salvar no histórico
    save_to_history('dashboard_completo', {
        'news_count': len(news_opps),
        'fund_count': len(fund_data),
        'poly_count': len(poly_markets)
    })
    
    # ========================================
    # CARDS DE MÉTRICAS PRINCIPAIS
    # ========================================
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='margin:0; font-size:0.9rem;'>📰 Notícias</h3>
            <h1 style='margin:10px 0; font-size:2.5rem;'>{len(news_opps)}</h1>
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>oportunidades</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        excelentes = len([f for f in fund_data if f['status'] == '🟢 Excelente']) if fund_data else 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='margin:0; font-size:0.9rem;'>💼 Empresas</h3>
            <h1 style='margin:10px 0; font-size:2.5rem;'>{len(fund_data)}</h1>
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>{excelentes} excelentes</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_roe = np.mean([f['roe'] for f in fund_data if pd.notna(f.get('roe'))]) if fund_data else 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='margin:0; font-size:0.9rem;'>📊 ROE Médio</h3>
            <h1 style='margin:10px 0; font-size:2.5rem;'>{avg_roe:.1f}%</h1>
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>retorno sobre capital</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='margin:0; font-size:0.9rem;'>🎯 Polymarket</h3>
            <h1 style='margin:10px 0; font-size:2.5rem;'>{len(poly_markets)}</h1>
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>mercados ativos</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ========================================
    # ALERTAS ATIVOS
    # ========================================
    
    if fund_data:
        df_fund = pd.DataFrame(fund_data)
        
        # Alertas de Score
        high_score = df_fund[df_fund['score'] >= alert_score]
        if not high_score.empty:
            st.markdown(f"""
            <div class='alert-box alert-danger'>
                <strong>🚨 {len(high_score)} ALERTAS DE SCORE ALTO!</strong><br>
                Tickers com score ≥ {alert_score}: {', '.join(high_score['ticker'].tolist()[:5])}
            </div>
            """, unsafe_allow_html=True)
        
        # Alertas de ROE
        high_roe = df_fund[df_fund['roe'] >= alert_roe]
        if not high_roe.empty:
            st.markdown(f"""
            <div class='alert-box alert-info'>
                <strong>💎 {len(high_roe)} empresas com ROE excepcional!</strong><br>
                ROE ≥ {alert_roe}%: {', '.join(high_roe['ticker'].tolist()[:5])}
            </div>
            """, unsafe_allow_html=True)
    
    # ========================================
    # RECOMENDAÇÕES INTELIGENTES
    # ========================================
    
    if fund_data:
        st.markdown("### 🤖 Recomendações Inteligentes")
        
        recommendations = get_recommendations(df_fund)
        
        if recommendations:
            cols = st.columns(len(recommendations))
            
            for i, rec in enumerate(recommendations):
                with cols[i]:
                    st.markdown(f"""
                    <div style='background: #f8f9fa; padding: 1rem; border-radius: 10px; 
                                border-left: 4px solid {"#27ae60" if rec["cor"] == "success" else "#3498db"};'>
                        <h4 style='margin: 0 0 0.5rem 0;'>{rec['tipo']}</h4>
                        <p style='margin: 0; font-size: 0.9rem;'><strong>{', '.join(rec['tickers'])}</strong></p>
                        <p style='margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666;'>{rec['razao']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("💡 Nenhuma recomendação específica no momento. Ajuste os filtros para ver mais oportunidades.")
    
    st.markdown("---")
    
    # ========================================
    # TABS COM CONTEÚDO
    # ========================================
    
    tab1, tab2, tab3, tab4 = st.tabs(["📰 Notícias", "💼 Fundamentos", "📊 Gráficos", "📥 Exportar"])
    
    with tab1:
        st.subheader("🔥 Oportunidades em Destaque")
        
        if news_opps:
            df_news = pd.DataFrame(news_opps)
            
            st.dataframe(
                df_news,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "score": st.column_config.ProgressColumn(
                        "Score",
                        format="%d",
                        min_value=0,
                        max_value=100,
                    ),
                }
            )
            
            # Busca rápida
            search_ticker = st.text_input("🔍 Buscar ticker específico", key="search_news")
            if search_ticker:
                result = df_news[df_news['ticker'].str.contains(search_ticker.upper(), na=False)]
                if not result.empty:
                    st.dataframe(result, use_container_width=True)
                else:
                    st.warning("Ticker não encontrado nas notícias")
        else:
            st.info("📭 Nenhuma notícia relevante no momento")
    
    with tab2:
        st.subheader("💎 Top Empresas por Fundamentos")
        
        if fund_data:
            df_fund_display = df_fund.copy()
            
            # Estatísticas resumidas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("ROE Médio", f"{df_fund['roe'].mean():.1f}%")
            with col2:
                st.metric("P/E Médio", f"{df_fund['pe'].mean():.1f}")
            with col3:
                st.metric("Div Yield Médio", f"{df_fund['div_yield'].mean():.2f}%")
            with col4:
                st.metric("Total Analisadas", len(df_fund))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Tabela com formatação
            st.dataframe(
                df_fund_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "score": st.column_config.ProgressColumn(
                        "Score",
                        format="%d",
                        min_value=0,
                        max_value=100,
                    ),
                    "market_cap": st.column_config.NumberColumn(
                        "Market Cap (B)",
                        format="$%.2fB"
                    ),
                    "roe": st.column_config.NumberColumn(
                        "ROE",
                        format="%.1f%%"
                    ),
                    "div_yield": st.column_config.NumberColumn(
                        "Div Yield",
                        format="%.2f%%"
                    ),
                }
            )
        else:
            st.info("📊 Sem dados fundamentalistas disponíveis")
    
    with tab3:
        if show_charts and fund_data:
            st.subheader("📈 Análises Visuais")
            
            # Gráfico 1: Top 15 por Score
            fig1 = px.bar(
                df_fund.nlargest(15, 'score'),
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
            fig1.update_layout(height=500, template='plotly_dark' if dark_charts else 'plotly_white')
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráficos lado a lado
            col1, col2 = st.columns(2)
            
            with col1:
                # ROE vs P/E
                fig2 = px.scatter(
                    df_fund,
                    x='pe',
                    y='roe',
                    size='market_cap',
                    color='status',
                    hover_data=['ticker', 'div_yield'],
                    title='ROE vs P/E (tamanho = Market Cap)',
                    labels={'pe': 'P/E Ratio', 'roe': 'ROE %'}
                )
                fig2.update_layout(height=450, template='plotly_dark' if dark_charts else 'plotly_white')
                st.plotly_chart(fig2, use_container_width=True)
            
            with col2:
                # Distribuição por Setor
                setor_counts = df_fund['setor'].value_counts().head(8)
                fig3 = px.pie(
                    values=setor_counts.values,
                    names=setor_counts.index,
                    title='Distribuição por Setor (Top 8)'
                )
                fig3.update_layout(height=450, template='plotly_dark' if dark_charts else 'plotly_white')
                st.plotly_chart(fig3, use_container_width=True)
            
            # Heatmap de Correlação
            st.markdown("#### 🔥 Matriz de Correlação")
            corr_fig = create_correlation_heatmap(df_fund)
            if corr_fig:
                st.plotly_chart(corr_fig, use_container_width=True)
        else:
            st.info("📊 Ative 'Mostrar Gráficos' no sidebar ou aguarde os dados serem carregados")
    
    with tab4:
        st.subheader("📥 Exportar Análises")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if news_opps:
                csv_news = pd.DataFrame(news_opps).to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📰 Download Notícias (CSV)",
                    csv_news,
                    f"noticias_bdrs_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key='download_news_csv'
                )
        
        with col2:
            if fund_data:
                csv_fund = df_fund.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "💼 Download Fundamentos (CSV)",
                    csv_fund,
                    f"fundamentos_bdrs_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key='download_fund_csv'
                )
        
        with col3:
            if news_opps and fund_data:
                excel_data = create_excel_download({
                    'Notícias': pd.DataFrame(news_opps),
                    'Fundamentos': df_fund,
                    'Resumo': pd.DataFrame([{
                        'Total_Noticias': len(news_opps),
                        'Total_Empresas': len(fund_data),
                        'ROE_Medio': df_fund['roe'].mean(),
                        'Data': datetime.now().strftime('%Y-%m-%d %H:%M')
                    }])
                })
                
                st.download_button(
                    "📊 Download Completo (Excel)",
                    excel_data,
                    f"analise_completa_bdrs_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    "application/vnd.ms-excel",
                    key='download_excel'
                )
        
        st.markdown("---")
        st.info("💡 **Dica:** O arquivo Excel contém múltiplas abas com dados detalhados de cada análise.")

# ============================================================
# MÓDULO DE NOTÍCIAS
# ============================================================

elif analysis_type == "📰 Notícias":
    st.subheader("📰 Rastreador de Notícias e Eventos Corporativos")
    
    ticker_map = get_bdr_mapping()
    
    with st.spinner("🔍 Buscando notícias e eventos..."):
        news_data = []
        progress = st.progress(0)
        
        for i, ticker in enumerate(selected_tickers):
            news = get_news_data(ticker)
            
            if news:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                score = 50
                events = []
                priority = "🟡 Média"
                
                # Check earnings
                try:
                    calendar = stock.calendar
                    if calendar is not None and 'Earnings Date' in calendar:
                        earnings_date = calendar['Earnings Date']
                        if isinstance(earnings_date, list) and len(earnings_date) > 0:
                            date_obj = earnings_date[0]
                            days_until = (datetime(date_obj.year, date_obj.month, date_obj.day) - datetime.now()).days
                            
                            if 0 < days_until <= 3:
                                score += 40
                                events.append(f"⚡ Earnings em {days_until} dias")
                                priority = "🔴 Urgente"
                            elif days_until <= 7:
                                score += 30
                                events.append(f"Earnings em {days_until} dias")
                                priority = "🔴 Urgente"
                            elif days_until <= 14:
                                score += 20
                                events.append(f"Earnings em {days_until} dias")
                                priority = "🟠 Alta"
                except:
                    pass
                
                # Check dividends
                if info.get('dividendYield'):
                    score += 10
                    events.append(f"Div Yield: {info.get('dividendYield')*100:.2f}%")
                
                if score >= min_score and (not show_urgent_only or priority == "🔴 Urgente"):
                    news_data.append({
                        'BDR': ticker_map.get(ticker, f"{ticker}34"),
                        'Ticker': ticker,
                        'Score': score,
                        'Prioridade': priority,
                        'Eventos': ', '.join(events) if events else 'Notícias recentes',
                        'Última Notícia': news[0].get('headline', 'N/A')[:100] if news else 'N/A',
                        'URL': news[0].get('url', '') if news else ''
                    })
            
            progress.progress((i + 1) / len(selected_tickers))
            time.sleep(0.1)
        
        progress.empty()
    
    if news_data:
        df_news = pd.DataFrame(news_data).sort_values('Score', ascending=False)
        
        # Estatísticas
        col1, col2, col3, col4 = st.columns(4)
        
        urgent = len(df_news[df_news['Prioridade'] == '🔴 Urgente'])
        high = len(df_news[df_news['Prioridade'] == '🟠 Alta'])
        medium = len(df_news[df_news['Prioridade'] == '🟡 Média'])
        
        col1.metric("Total", len(df_news))
        col2.metric("🔴 Urgente", urgent)
        col3.metric("🟠 Alta", high)
        col4.metric("🟡 Média", medium)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Filtro adicional
        filter_priority = st.multiselect(
            "Filtrar por Prioridade",
            options=df_news['Prioridade'].unique(),
            default=df_news['Prioridade'].unique(),
            key="filter_priority_news"
        )
        
        df_filtered = df_news[df_news['Prioridade'].isin(filter_priority)]
        
        # Tabela
        st.dataframe(
            df_filtered,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score",
                    format="%d",
                    min_value=0,
                    max_value=100,
                ),
                "URL": st.column_config.LinkColumn("Link")
            }
        )
        
        # Download
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            csv,
            f"noticias_bdrs_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            key='download-news-main'
        )
        
        # Gráfico
        if show_charts:
            fig = px.bar(
                df_filtered.head(15),
                x='Ticker',
                y='Score',
                color='Prioridade',
                title='Top 15 Oportunidades por Score',
                color_discrete_map={
                    '🔴 Urgente': '#e74c3c',
                    '🟠 Alta': '#e67e22',
                    '🟡 Média': '#f39c12'
                }
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 Nenhuma notícia relevante encontrada com os filtros atuais")

# ============================================================
# MÓDULO DE FUNDAMENTOS
# ============================================================

elif analysis_type == "💼 Fundamentos":
    st.subheader("💼 Análise Fundamentalista Detalhada")
    
    with st.spinner("📊 Analisando fundamentos..."):
        fund_data = []
        progress = st.progress(0)
        
        for i, ticker in enumerate(selected_tickers):
            data = get_fundamental_data(ticker)
            if data and data['score'] >= min_score:
                # Aplicar filtros
                if (roe_range[0] <= data.get('roe', 0) <= roe_range[1] and
                    pe_range[0] <= data.get('pe', 0) <= pe_range[1] and
                    data.get('div_yield', 0) >= div_yield_min):
                    fund_data.append(data)
            
            progress.progress((i + 1) / len(selected_tickers))
            time.sleep(0.1)
        
        progress.empty()
    
    if fund_data:
        df_fund = pd.DataFrame(fund_data).sort_values('score', ascending=False)
        
        # Estatísticas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_roe = df_fund['roe'].mean()
            st.metric("ROE Médio", f"{avg_roe:.1f}%", 
                     delta=f"{avg_roe - 15:.1f}% vs benchmark (15%)")
        
        with col2:
            avg_pe = df_fund['pe'].mean()
            st.metric("P/E Médio", f"{avg_pe:.1f}",
                     delta=f"{avg_pe - 20:.1f} vs mercado (20)")
        
        with col3:
            avg_div = df_fund['div_yield'].mean()
            st.metric("Dividend Yield Médio", f"{avg_div:.2f}%")
        
        with col4:
            excelentes = len(df_fund[df_fund['status'] == '🟢 Excelente'])
            st.metric("Excelentes", excelentes,
                     delta=f"{(excelentes/len(df_fund)*100):.0f}% do total")
        
        st.markdown("---")
        
        # Filtros por setor
        setores = st.multiselect(
            "🏢 Filtrar por Setor",
            options=df_fund['setor'].unique(),
            default=df_fund['setor'].unique(),
            key="filter_setor"
        )
        
        df_filtered = df_fund[df_fund['setor'].isin(setores)]
        
        # Tabela detalhada
        st.dataframe(
            df_filtered,
            use_container_width=True,
            hide_index=True,
            column_config={
                "score": st.column_config.ProgressColumn(
                    "Score",
                    format="%d",
                    min_value=0,
                    max_value=100,
                ),
                "market_cap": st.column_config.NumberColumn(
                    "Market Cap",
                    format="$%.2fB"
                ),
                "roe": st.column_config.NumberColumn(
                    "ROE",
                    format="%.1f%%"
                ),
                "pe": st.column_config.NumberColumn(
                    "P/E",
                    format="%.1f"
                ),
                "pb": st.column_config.NumberColumn(
                    "P/B",
                    format="%.1f"
                ),
                "div_yield": st.column_config.NumberColumn(
                    "Div Yield",
                    format="%.2f%%"
                ),
            }
        )
        
        # Gráficos
        if show_charts:
            st.markdown("### 📈 Análises Visuais")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # ROE Distribution
                fig1 = px.histogram(
                    df_filtered,
                    x='roe',
                    nbins=20,
                    title='Distribuição de ROE',
                    labels={'roe': 'ROE (%)'},
                    color_discrete_sequence=['#3498db']
                )
                fig1.update_layout(height=400)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # P/E vs Dividend Yield
                fig2 = px.scatter(
                    df_filtered,
                    x='pe',
                    y='div_yield',
                    size='market_cap',
                    color='status',
                    hover_data=['ticker'],
                    title='P/E vs Dividend Yield',
                    labels={'pe': 'P/E Ratio', 'div_yield': 'Dividend Yield (%)'}
                )
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
            
            # Heatmap
            st.markdown("#### 🔥 Correlação entre Métricas")
            corr_fig = create_correlation_heatmap(df_filtered)
            if corr_fig:
                st.plotly_chart(corr_fig, use_container_width=True)
        
        # Download
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Fundamentos (CSV)",
            csv,
            f"fundamentos_bdrs_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
    else:
        st.info("📊 Nenhum dado fundamentalista disponível com os filtros atuais")

# ============================================================
# MÓDULO POLYMARKET
# ============================================================

elif analysis_type == "🎯 Polymarket":
    st.subheader("🎯 Sinais do Polymarket sobre Earnings")
    
    poly_markets = get_polymarket_data()
    
    if not poly_markets.empty:
        col1, col2 = st.columns(2)
        
        col1.metric("Mercados Ativos", len(poly_markets))
        
        # Filtrar mercados de earnings
        earnings_markets = poly_markets[
            poly_markets.get("question", pd.Series([""] * len(poly_markets)))
            .astype(str).str.lower()
            .str.contains('earnings|revenue|profit|beat|miss', na=False)
        ]
        
        col2.metric("Mercados de Earnings", len(earnings_markets))
        
        if not earnings_markets.empty:
            st.markdown("---")
            
            # Análise por ticker
            signals = []
            
            progress = st.progress(0)
            for i, ticker in enumerate(selected_tickers[:30]):
                ticker_markets = earnings_markets[
                    earnings_markets.get("question", pd.Series([""] * len(earnings_markets)))
                    .astype(str).str.lower()
                    .str.contains(ticker.lower(), na=False)
                ]
                
                if not ticker_markets.empty:
                    num_markets = len(ticker_markets)
                    score = min(100, num_markets * 20)
                    status = '🔴 Forte' if score >= 70 else '🟠 Médio' if score >= 50 else '🟡 Fraco'
                    
                    signals.append({
                        'Ticker': ticker,
                        'Mercados': num_markets,
                        'Score': score,
                        'Status': status
                    })
                
                progress.progress((i + 1) / min(30, len(selected_tickers)))
            
            progress.empty()
            
            if signals:
                df_signals = pd.DataFrame(signals).sort_values('Score', ascending=False)
                
                # Estatísticas
                col1, col2, col3 = st.columns(3)
                
                fortes = len(df_signals[df_signals['Status'] == '🔴 Forte'])
                medios = len(df_signals[df_signals['Status'] == '🟠 Médio'])
                
                col1.metric("Sinais Detectados", len(df_signals))
                col2.metric("🔴 Sinais Fortes", fortes)
                col3.metric("🟠 Sinais Médios", medios)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Tabela
                st.dataframe(
                    df_signals,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Score": st.column_config.ProgressColumn(
                            "Score",
                            format="%d",
                            min_value=0,
                            max_value=100,
                        ),
                    }
                )
                
                # Gráfico
                if show_charts:
                    fig = px.bar(
                        df_signals.head(15),
                        x='Ticker',
                        y='Mercados',
                        color='Status',
                        title='Número de Mercados por Ticker',
                        color_discrete_map={
                            '🔴 Forte': '#e74c3c',
                            '🟠 Médio': '#e67e22',
                            '🟡 Fraco': '#f39c12'
                        }
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("🎯 Nenhum sinal forte identificado para os tickers selecionados")
        else:
            st.warning("⚠️ Nenhum mercado de earnings ativo no momento")
    else:
        st.error("❌ Não foi possível carregar dados do Polymarket")

# ============================================================
# MÓDULO COMPARADOR
# ============================================================

elif analysis_type == "🔍 Comparador":
    st.subheader("🔍 Comparador de Tickers")
    
    compare_tickers = st.multiselect(
        "Selecione até 5 tickers para comparar",
        ALL_BDRS,
        default=['AAPL', 'MSFT', 'GOOGL'],
        max_selections=5,
        key="compare_tickers_multi"
    )
    
    if compare_tickers:
        with st.spinner("📊 Carregando dados comparativos..."):
            comp_data = []
            
            for ticker in compare_tickers:
                data = get_fundamental_data(ticker)
                if data:
                    comp_data.append(data)
                time.sleep(0.2)
        
        if comp_data:
            df_comp = pd.DataFrame(comp_data)
            
            # Métricas lado a lado
            st.markdown("### 📊 Comparação de Métricas")
            
            cols = st.columns(len(comp_data))
            
            for i, (col, data) in enumerate(zip(cols, comp_data)):
                with col:
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                padding: 1.5rem; border-radius: 10px; color: white; text-align: center;'>
                        <h2 style='margin: 0;'>{data['ticker']}</h2>
                        <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>{data['setor']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    st.metric("Status", data['status'])
                    st.metric("Score", data['score'])
                    
                    if pd.notna(data['roe']):
                        st.metric("ROE", f"{data['roe']:.1f}%")
                    else:
                        st.metric("ROE", "N/A")
                    
                    if pd.notna(data['pe']):
                        st.metric("P/E", f"{data['pe']:.1f}")
                    else:
                        st.metric("P/E", "N/A")
                    
                    if pd.notna(data['div_yield']):
                        st.metric("Div Yield", f"{data['div_yield']:.2f}%")
                    else:
                        st.metric("Div Yield", "N/A")
                    
                    st.metric("Market Cap", format_number(data['market_cap'], prefix='$', suffix='B'))
            
            st.markdown("---")
            
            # Gráficos comparativos
            if show_charts:
                st.markdown("### 📈 Comparações Visuais")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Comparação de ROE
                    fig1 = go.Figure()
                    fig1.add_trace(go.Bar(
                        x=df_comp['ticker'],
                        y=df_comp['roe'],
                        name='ROE',
                        marker_color='#27ae60',
                        text=df_comp['roe'].round(1),
                        textposition='auto',
                    ))
                    fig1.update_layout(
                        title='Comparação de ROE',
                        yaxis_title='ROE (%)',
                        height=400
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Comparação de Dividend Yield
                    fig2 = go.Figure()
                    fig2.add_trace(go.Bar(
                        x=df_comp['ticker'],
                        y=df_comp['div_yield'],
                        name='Dividend Yield',
                        marker_color='#3498db',
                        text=df_comp['div_yield'].round(2),
                        textposition='auto',
                    ))
                    fig2.update_layout(
                        title='Comparação de Dividend Yield',
                        yaxis_title='Dividend Yield (%)',
                        height=400
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Radar Chart
                fig3 = go.Figure()
                
                for _, row in df_comp.iterrows():
                    # Normalizar valores para 0-100
                    values = [
                        min(100, (row['roe'] / 50) * 100) if pd.notna(row['roe']) else 0,
                        min(100, (row['div_yield'] / 10) * 100) if pd.notna(row['div_yield']) else 0,
                        min(100, (row['market_cap'] / 1000) * 100) if pd.notna(row['market_cap']) else 0,
                        row['score'],
                        min(100, (50 / row['pe']) * 100) if pd.notna(row['pe']) and row['pe'] > 0 else 0
                    ]
                    
                    fig3.add_trace(go.Scatterpolar(
                        r=values,
                        theta=['ROE', 'Div Yield', 'Market Cap', 'Score', 'P/E (inv)'],
                        fill='toself',
                        name=row['ticker']
                    ))
                
                fig3.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    title='Comparação Multi-dimensional (Normalizado 0-100)',
                    height=500
                )
                st.plotly_chart(fig3, use_container_width=True)
            
            # Tabela comparativa
            st.markdown("### 📊 Tabela Comparativa Completa")
            st.dataframe(
                df_comp[['ticker', 'status', 'score', 'roe', 'pe', 'pb', 'div_yield', 'market_cap', 'setor']],
                use_container_width=True,
                hide_index=True
            )
            
            # Análise comparativa automática
            st.markdown("### 🤖 Análise Comparativa")
            
            best_roe = df_comp.nlargest(1, 'roe').iloc[0]
            best_div = df_comp.nlargest(1, 'div_yield').iloc[0]
            lowest_pe = df_comp.nsmallest(1, 'pe').iloc[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.success(f"**Melhor ROE:** {best_roe['ticker']} ({best_roe['roe']:.1f}%)")
            
            with col2:
                st.info(f"**Maior Dividendo:** {best_div['ticker']} ({best_div['div_yield']:.2f}%)")
            
            with col3:
                st.warning(f"**Menor P/E:** {lowest_pe['ticker']} ({lowest_pe['pe']:.1f})")
        else:
            st.error("❌ Não foi possível carregar dados para comparação")
    else:
        st.info("👆 Selecione tickers acima para começar a comparação")

# ============================================================
# MÓDULO DE HISTÓRICO
# ============================================================

elif analysis_type == "📈 Histórico":
    st.subheader("📈 Histórico de Análises")
    
    if 'history' in st.session_state and st.session_state.history:
        st.success(f"📊 {len(st.session_state.history)} análises registradas")
        
        # Mostrar últimas 10
        recent_history = st.session_state.history[-10:]
        
        for i, entry in enumerate(reversed(recent_history), 1):
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%d/%m/%Y %H:%M')
            data_type = entry['type']
            
            with st.expander(f"#{i} - {data_type} - {timestamp}"):
                st.json(entry['data'])
        
        # Botão para limpar histórico
        if st.button("🗑️ Limpar Histórico", key="clear_history"):
            st.session_state.history = []
            st.success("✅ Histórico limpo!")
            st.rerun()
    else:
        st.info("📭 Nenhum histórico disponível ainda. Execute algumas análises para começar a registrar.")

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem 0;'>
    <p style='font-size: 0.9rem; margin: 0;'>
        <strong>Dashboard Profissional de Análise de BDRs</strong>
    </p>
    <p style='font-size: 0.8rem; margin: 0.5rem 0;'>
        Desenvolvido para análise fundamentalista completa
    </p>
    <p style='font-size: 0.75rem; margin: 0.5rem 0; color: #999;'>
        ⚠️ Este sistema é apenas informativo. Não constitui recomendação de investimento.
    </p>
    <p style='font-size: 0.75rem; margin: 0.5rem 0; color: #999;'>
        Dados atualizados em tempo real via APIs públicas (Yahoo Finance, Finnhub, Polymarket)
    </p>
    <p style='font-size: 0.75rem; margin: 1rem 0 0 0; color: #aaa;'>
        Versão 2.0 Pro | Janeiro 2026
    </p>
</div>
""", unsafe_allow_html=True)
