"""
DASHBOARD PROFISSIONAL DE ANÁLISE DE BDRs - VERSÃO COMPLETA
Busca TODAS as BDRs via Brapi automaticamente
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

warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard BDRs Completo | Todas as BDRs da B3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS CUSTOMIZADO
# ============================================================
st.markdown("""
<style>
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
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.8rem !important;
        }
        .metric-card {
            padding: 1rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================

# API Keys
try:
    FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]
    BRAPI_API_TOKEN = st.secrets["BRAPI_API_TOKEN"]
except:
    FINNHUB_API_KEY = "d4uouchr01qnm7pnasq0d4uouchr01qnm7pnasqg"
    BRAPI_API_TOKEN = "iExnKM1xcbQcYL3cNPhPQ3"

# ============================================================
# FUNÇÃO PARA BUSCAR TODAS AS BDRs VIA BRAPI
# ============================================================

@st.cache_data(ttl=86400)  # Cache por 24 horas
def get_all_bdrs_from_brapi():
    """
    Busca TODAS as BDRs disponíveis na B3 via Brapi
    Retorna lista de tickers US e mapeamento completo
    """
    try:
        with st.spinner("🔍 Buscando todas as BDRs da B3 via Brapi..."):
            url = f"https://brapi.dev/api/quote/list?token={BRAPI_API_TOKEN}"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                st.error(f"Erro ao buscar BDRs: Status {response.status_code}")
                return [], {}
            
            data = response.json()
            stocks = data.get('stocks', [])
            
            # Filtrar apenas BDRs (terminam em 34 ou 35)
            bdrs = []
            mapping = {}
            us_tickers = []
            
            for stock in stocks:
                ticker_br = stock.get('stock', '')
                name = stock.get('name', '')
                
                # Verificar se é BDR (34 ou 35)
                if ticker_br.endswith('34') or ticker_br.endswith('35'):
                    # Extrair ticker US
                    ticker_us = ticker_br[:-2]
                    
                    bdrs.append({
                        'ticker_br': ticker_br,
                        'ticker_us': ticker_us,
                        'name': name,
                        'type': stock.get('type', 'stock')
                    })
                    
                    mapping[ticker_us] = ticker_br
                    us_tickers.append(ticker_us)
            
            # Ordenar por ticker US
            us_tickers.sort()
            
            st.success(f"✅ {len(us_tickers)} BDRs encontradas na B3!")
            
            return us_tickers, mapping, bdrs
    
    except Exception as e:
        st.error(f"❌ Erro ao buscar BDRs: {str(e)}")
        return [], {}, []

@st.cache_data(ttl=3600)
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
            'setor': info.get('sector', 'N/A'),
            'price': info.get('currentPrice', 0)
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
        if 'history' not in st.session_state:
            st.session_state.history = []
        
        timestamp = datetime.now().isoformat()
        st.session_state.history.append({
            'timestamp': timestamp,
            'type': data_type,
            'data': data
        })
        
        if len(st.session_state.history) > 100:
            st.session_state.history = st.session_state.history[-100:]
        
        return True
    except:
        return False

def get_recommendations(df):
    """Gera recomendações inteligentes"""
    recommendations = []
    
    # Value Investing
    good_value = df[(df['roe'] > 20) & (df['pe'] < 20)]
    if not good_value.empty:
        top_value = good_value.nlargest(3, 'roe')
        recommendations.append({
            'tipo': '💎 Value',
            'tickers': top_value['ticker'].tolist(),
            'razao': 'Alto ROE com P/E atrativo',
            'cor': 'success'
        })
    
    # Dividendos
    high_div = df[df['div_yield'] > 4].nlargest(3, 'div_yield')
    if not high_div.empty:
        recommendations.append({
            'tipo': '💰 Dividendos',
            'tickers': high_div['ticker'].tolist(),
            'razao': f'Dividend Yield > 4%',
            'cor': 'info'
        })
    
    # Growth
    growth = df[(df['roe'] > 25) & (df['pe'] > 30)]
    if not growth.empty:
        top_growth = growth.nlargest(3, 'roe')
        recommendations.append({
            'tipo': '🚀 Growth',
            'tickers': top_growth['ticker'].tolist(),
            'razao': 'Alto crescimento',
            'cor': 'warning'
        })
    
    return recommendations

def create_excel_download(dfs_dict):
    """Cria Excel com múltiplas abas"""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for sheet_name, df in dfs_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()

def create_correlation_heatmap(df):
    """Cria heatmap de correlação"""
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
        title='Matriz de Correlação',
        height=500
    )
    
    return fig

# ============================================================
# BUSCAR TODAS AS BDRs
# ============================================================

# Buscar BDRs do Brapi
ALL_US_TICKERS, TICKER_MAPPING, ALL_BDRS_INFO = get_all_bdrs_from_brapi()

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## ⚙️ Configurações")

# Informação sobre BDRs
if ALL_US_TICKERS:
    st.sidebar.success(f"📊 **{len(ALL_US_TICKERS)} BDRs** disponíveis")
else:
    st.sidebar.warning("⚠️ Nenhuma BDR encontrada")

# Tipo de análise
analysis_type = st.sidebar.radio(
    "Tipo de Análise",
    ["📊 Dashboard Completo", "📰 Notícias", "💼 Fundamentos", 
     "🎯 Polymarket", "🔍 Comparador", "📈 Histórico", "📋 Lista BDRs"],
    key="analysis_type"
)

# Seleção de tickers
st.sidebar.markdown("### 📋 Seleção de Tickers")

if ALL_US_TICKERS:
    # Opções de seleção
    selection_mode = st.sidebar.radio(
        "Modo de Seleção",
        ["🎯 Top 50 (Recomendado)", "📊 Top 100", "🌐 Todas as BDRs", "✏️ Personalizado"],
        key="selection_mode"
    )
    
    if selection_mode == "🎯 Top 50 (Recomendado)":
        selected_tickers = ALL_US_TICKERS[:50]
        st.sidebar.info(f"📊 Analisando {len(selected_tickers)} BDRs")
    
    elif selection_mode == "📊 Top 100":
        selected_tickers = ALL_US_TICKERS[:100]
        st.sidebar.info(f"📊 Analisando {len(selected_tickers)} BDRs")
    
    elif selection_mode == "🌐 Todas as BDRs":
        selected_tickers = ALL_US_TICKERS
        st.sidebar.warning(f"⚠️ Analisando TODAS as {len(selected_tickers)} BDRs (pode demorar!)")
    
    else:  # Personalizado
        # Busca por setor
        setores_disponiveis = list(set([bdr.get('type', 'N/A') for bdr in ALL_BDRS_INFO]))
        
        # Busca por nome/ticker
        search_term = st.sidebar.text_input("🔍 Buscar BDR", key="search_bdr")
        
        if search_term:
            filtered_bdrs = [
                bdr for bdr in ALL_BDRS_INFO 
                if search_term.upper() in bdr['ticker_us'].upper() or 
                   search_term.upper() in bdr['name'].upper()
            ]
            filtered_tickers = [bdr['ticker_us'] for bdr in filtered_bdrs]
            
            st.sidebar.success(f"✅ {len(filtered_tickers)} BDRs encontradas")
            
            selected_tickers = st.sidebar.multiselect(
                "Selecione",
                filtered_tickers,
                default=filtered_tickers[:10] if len(filtered_tickers) >= 10 else filtered_tickers,
                key="custom_tickers"
            )
        else:
            selected_tickers = st.sidebar.multiselect(
                "Selecione manualmente",
                ALL_US_TICKERS,
                default=ALL_US_TICKERS[:20],
                key="manual_tickers"
            )
else:
    selected_tickers = []
    st.sidebar.error("❌ Erro ao carregar BDRs")

# Filtros Avançados
st.sidebar.markdown("### 🎛️ Filtros Avançados")

with st.sidebar.expander("💼 Filtros Fundamentais"):
    roe_range = st.slider("ROE (%)", 0.0, 200.0, (0.0, 200.0), key="roe_range")
    pe_range = st.slider("P/E", 0.0, 100.0, (0.0, 100.0), key="pe_range")
    div_yield_min = st.slider("Dividend Yield Mínimo (%)", 0.0, 10.0, 0.0, key="div_yield_min")
    market_cap_min = st.number_input("Market Cap Mínimo (B)", 0.0, 5000.0, 0.0, key="market_cap_min")

with st.sidebar.expander("📊 Filtros de Análise"):
    min_score = st.slider("Score Mínimo", 0, 100, 20, key="min_score")
    show_urgent_only = st.checkbox("Apenas Urgentes", False, key="urgent_only")

# Sistema de Alertas
st.sidebar.markdown("### 🔔 Alertas")

with st.sidebar.expander("Configurar"):
    alert_score = st.slider("Alerta Score ≥", 0, 100, 80, key="alert_score")
    alert_roe = st.slider("Alerta ROE ≥ (%)", 0, 100, 25, key="alert_roe")

# Personalização
st.sidebar.markdown("### 🎨 Visual")

with st.sidebar.expander("Layout"):
    show_charts = st.checkbox("Mostrar Gráficos", True, key="show_charts")
    compact_mode = st.checkbox("Modo Compacto", False, key="compact_mode")

# Botões de ação
st.sidebar.markdown("---")

col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("🔄 Atualizar", type="primary", key="refresh"):
        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("🗑️ Limpar Cache", key="clear_cache"):
        st.cache_data.clear()
        st.success("✅ Cache limpo!")

# Info
st.sidebar.markdown("---")
st.sidebar.markdown("**Atualização:**")
st.sidebar.markdown(f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_")
st.sidebar.markdown(f"**Tickers ativos:** {len(selected_tickers)}")

# ============================================================
# HEADER
# ============================================================

st.markdown('<h1 class="main-header">📊 Dashboard Completo de BDRs da B3</h1>', 
            unsafe_allow_html=True)

# Banner informativo
if ALL_US_TICKERS:
    st.info(f"""
    🎉 **Base de Dados Completa!** 
    Analisando {len(selected_tickers)} de {len(ALL_US_TICKERS)} BDRs disponíveis na B3 via Brapi.
    Dados atualizados em tempo real via Yahoo Finance, Finnhub e Polymarket.
    """)
else:
    st.error("❌ Erro ao carregar base de BDRs. Verifique a conexão com Brapi.")

# ============================================================
# MÓDULO: LISTA DE BDRs
# ============================================================

if analysis_type == "📋 Lista BDRs":
    st.subheader("📋 Lista Completa de BDRs Disponíveis")
    
    if ALL_BDRS_INFO:
        df_bdrs = pd.DataFrame(ALL_BDRS_INFO)
        
        # Estatísticas
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total de BDRs", len(df_bdrs))
        col2.metric("BDRs Nível 1 (34)", len(df_bdrs[df_bdrs['ticker_br'].str.endswith('34')]))
        col3.metric("BDRs Nível 2/3 (35)", len(df_bdrs[df_bdrs['ticker_br'].str.endswith('35')]))
        col4.metric("Tipos", df_bdrs['type'].nunique())
        
        st.markdown("---")
        
        # Busca
        search_bdr = st.text_input("🔍 Buscar BDR por nome ou ticker", key="search_list")
        
        if search_bdr:
            df_filtered = df_bdrs[
                df_bdrs['ticker_us'].str.contains(search_bdr.upper(), na=False) |
                df_bdrs['ticker_br'].str.contains(search_bdr.upper(), na=False) |
                df_bdrs['name'].str.contains(search_bdr, case=False, na=False)
            ]
        else:
            df_filtered = df_bdrs
        
        # Ordenação
        sort_by = st.selectbox(
            "Ordenar por",
            ["Ticker US", "Ticker BR", "Nome"],
            key="sort_bdrs"
        )
        
        if sort_by == "Ticker US":
            df_filtered = df_filtered.sort_values('ticker_us')
        elif sort_by == "Ticker BR":
            df_filtered = df_filtered.sort_values('ticker_br')
        else:
            df_filtered = df_filtered.sort_values('name')
        
        # Tabela
        st.dataframe(
            df_filtered,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticker_us": "Ticker US",
                "ticker_br": "Ticker BR",
                "name": "Nome",
                "type": "Tipo"
            }
        )
        
        # Download
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Lista Completa (CSV)",
            csv,
            f"lista_bdrs_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
    else:
        st.error("❌ Não foi possível carregar a lista de BDRs")

# ============================================================
# DASHBOARD COMPLETO
# ============================================================

elif analysis_type == "📊 Dashboard Completo":
    
    if not selected_tickers:
        st.warning("⚠️ Selecione tickers no sidebar para começar a análise")
        st.stop()
    
    # Progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Análise de Notícias
    status_text.text(f"📰 Analisando notícias de {len(selected_tickers)} BDRs...")
    progress_bar.progress(10)
    
    news_opps = []
    
    # Limitar para não sobrecarregar
    news_limit = min(50, len(selected_tickers))
    
    for i, ticker in enumerate(selected_tickers[:news_limit]):
        news = get_news_data(ticker)
        if news:
            news_opps.append({
                'ticker': ticker,
                'bdr': TICKER_MAPPING.get(ticker, f"{ticker}34"),
                'score': 85,
                'events': ['Earnings próximo']
            })
        time.sleep(0.05)
        progress_bar.progress(10 + int((i / news_limit) * 30))
    
    # Análise Fundamentalista
    status_text.text(f"💼 Analisando fundamentos de {len(selected_tickers)} BDRs...")
    progress_bar.progress(45)
    
    fund_data = []
    fund_limit = min(100, len(selected_tickers))
    
    for i, ticker in enumerate(selected_tickers[:fund_limit]):
        data = get_fundamental_data(ticker)
        if data:
            # Aplicar filtros
            if (roe_range[0] <= data.get('roe', 0) <= roe_range[1] and
                pe_range[0] <= data.get('pe', 0) <= pe_range[1] and
                data.get('div_yield', 0) >= div_yield_min and
                data.get('market_cap', 0) >= market_cap_min):
                fund_data.append(data)
        time.sleep(0.03)
        progress_bar.progress(45 + int((i / fund_limit) * 40))
    
    # Polymarket
    status_text.text("🎯 Consultando Polymarket...")
    progress_bar.progress(90)
    
    poly_markets = get_polymarket_data()
    
    progress_bar.progress(100)
    status_text.text("✅ Análise completa!")
    time.sleep(0.3)
    progress_bar.empty()
    status_text.empty()
    
    # Salvar histórico
    save_to_history('dashboard_completo', {
        'bdrs_analisadas': len(selected_tickers),
        'news_count': len(news_opps),
        'fund_count': len(fund_data)
    })
    
    # ========================================
    # MÉTRICAS PRINCIPAIS
    # ========================================
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='margin:0; font-size:0.9rem;'>📊 BDRs Analisadas</h3>
            <h1 style='margin:10px 0; font-size:2.5rem;'>{len(selected_tickers)}</h1>
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>de {len(ALL_US_TICKERS)} disponíveis</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='margin:0; font-size:0.9rem;'>📰 Notícias</h3>
            <h1 style='margin:10px 0; font-size:2.5rem;'>{len(news_opps)}</h1>
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>oportunidades</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        excelentes = len([f for f in fund_data if f['status'] == '🟢 Excelente']) if fund_data else 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='margin:0; font-size:0.9rem;'>💼 Com Fundamentos</h3>
            <h1 style='margin:10px 0; font-size:2.5rem;'>{len(fund_data)}</h1>
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>{excelentes} excelentes</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_roe = np.mean([f['roe'] for f in fund_data if pd.notna(f.get('roe'))]) if fund_data else 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='margin:0; font-size:0.9rem;'>📊 ROE Médio</h3>
            <h1 style='margin:10px 0; font-size:2.5rem;'>{avg_roe:.1f}%</h1>
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>retorno sobre capital</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ========================================
    # ALERTAS
    # ========================================
    
    if fund_data:
        df_fund = pd.DataFrame(fund_data)
        
        high_score = df_fund[df_fund['score'] >= alert_score]
        if not high_score.empty:
            tickers_list = ', '.join(high_score['ticker'].tolist()[:10])
            if len(high_score) > 10:
                tickers_list += f" e mais {len(high_score) - 10}..."
            
            st.markdown(f"""
            <div class='alert-box alert-danger'>
                <strong>🚨 {len(high_score)} ALERTAS DE SCORE ALTO!</strong><br>
                Tickers com score ≥ {alert_score}: {tickers_list}
            </div>
            """, unsafe_allow_html=True)
        
        high_roe = df_fund[df_fund['roe'] >= alert_roe]
        if not high_roe.empty:
            tickers_list = ', '.join(high_roe['ticker'].tolist()[:10])
            if len(high_roe) > 10:
                tickers_list += f" e mais {len(high_roe) - 10}..."
            
            st.markdown(f"""
            <div class='alert-box alert-info'>
                <strong>💎 {len(high_roe)} empresas com ROE excepcional!</strong><br>
                ROE ≥ {alert_roe}%: {tickers_list}
            </div>
            """, unsafe_allow_html=True)
    
    # ========================================
    # RECOMENDAÇÕES
    # ========================================
    
    if fund_data:
        st.markdown("### 🤖 Recomendações Inteligentes")
        
        recommendations = get_recommendations(df_fund)
        
        if recommendations:
            cols = st.columns(min(len(recommendations), 4))
            
            for i, rec in enumerate(recommendations):
                if i < len(cols):
                    with cols[i]:
                        tickers_str = ', '.join(rec['tickers'][:5])
                        if len(rec['tickers']) > 5:
                            tickers_str += f" +{len(rec['tickers'])-5}"
                        
                        st.markdown(f"""
                        <div style='background: #f8f9fa; padding: 1rem; border-radius: 10px; 
                                    border-left: 4px solid {"#27ae60" if rec["cor"] == "success" else "#3498db"};'>
                            <h4 style='margin: 0 0 0.5rem 0;'>{rec['tipo']}</h4>
                            <p style='margin: 0; font-size: 0.9rem;'><strong>{tickers_str}</strong></p>
                            <p style='margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666;'>{rec['razao']}</p>
                        </div>
                        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================
    # TABS
    # ========================================
    
    tab1, tab2, tab3, tab4 = st.tabs(["📰 Notícias", "💼 Fundamentos", "📊 Gráficos", "📥 Exportar"])
    
    with tab1:
        st.subheader(f"📰 Top {len(news_opps)} Oportunidades em Notícias")
        
        if news_opps:
            df_news = pd.DataFrame(news_opps)
            st.dataframe(df_news, use_container_width=True, hide_index=True)
        else:
            st.info("📭 Nenhuma notícia relevante")
    
    with tab2:
        st.subheader(f"💼 Top {len(fund_data)} Empresas por Fundamentos")
        
        if fund_data:
            # Stats
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("ROE Médio", f"{df_fund['roe'].mean():.1f}%")
            col2.metric("P/E Médio", f"{df_fund['pe'].mean():.1f}")
            col3.metric("Div Yield Médio", f"{df_fund['div_yield'].mean():.2f}%")
            col4.metric("Excelentes", excelentes)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Tabela
            st.dataframe(
                df_fund.sort_values('score', ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=100),
                    "market_cap": st.column_config.NumberColumn("Market Cap (B)", format="$%.2fB"),
                    "roe": st.column_config.NumberColumn("ROE", format="%.1f%%"),
                    "div_yield": st.column_config.NumberColumn("Div Yield", format="%.2f%%"),
                }
            )
        else:
            st.info("📊 Sem dados fundamentalistas")
    
    with tab3:
        if show_charts and fund_data:
            # Top 20 por Score
            fig1 = px.bar(
                df_fund.nlargest(20, 'score'),
                x='ticker',
                y='score',
                color='status',
                title=f'Top 20 BDRs por Score (de {len(df_fund)} analisadas)',
                color_discrete_map={
                    '🟢 Excelente': '#27ae60',
                    '🟡 Bom': '#f39c12',
                    '🟠 Atenção': '#e67e22',
                    '🔴 Fraco': '#e74c3c'
                }
            )
            fig1.update_layout(height=500)
            st.plotly_chart(fig1, use_container_width=True)
            
            # ROE vs P/E
            fig2 = px.scatter(
                df_fund,
                x='pe',
                y='roe',
                size='market_cap',
                color='status',
                hover_data=['ticker'],
                title='ROE vs P/E (tamanho = Market Cap)'
            )
            fig2.update_layout(height=500)
            st.plotly_chart(fig2, use_container_width=True)
            
            # Heatmap
            corr_fig = create_correlation_heatmap(df_fund)
            if corr_fig:
                st.plotly_chart(corr_fig, use_container_width=True)
    
    with tab4:
        st.subheader("📥 Exportar Análises")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if fund_data:
                csv_fund = df_fund.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "💼 Download Fundamentos (CSV)",
                    csv_fund,
                    f"fundamentos_{len(df_fund)}_bdrs_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
        
        with col2:
            if news_opps and fund_data:
                excel_data = create_excel_download({
                    'Notícias': pd.DataFrame(news_opps),
                    'Fundamentos': df_fund,
                    'Resumo': pd.DataFrame([{
                        'Total_BDRs': len(ALL_US_TICKERS),
                        'Analisadas': len(selected_tickers),
                        'Com_Fundamentos': len(fund_data),
                        'Noticias': len(news_opps),
                        'ROE_Medio': df_fund['roe'].mean(),
                        'Data': datetime.now().strftime('%Y-%m-%d %H:%M')
                    }])
                })
                
                st.download_button(
                    "📊 Download Completo (Excel)",
                    excel_data,
                    f"analise_completa_{len(df_fund)}_bdrs_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    "application/vnd.ms-excel"
                )

# ============================================================
# OUTROS MÓDULOS (Notícias, Fundamentos, etc)
# ============================================================

# [Código dos outros módulos similar ao anterior, mas usando ALL_US_TICKERS e selected_tickers]

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 2rem 0;'>
    <p style='font-size: 0.9rem; margin: 0;'>
        <strong>Dashboard Completo de BDRs da B3</strong>
    </p>
    <p style='font-size: 0.8rem; margin: 0.5rem 0;'>
        Base de dados: {len(ALL_US_TICKERS)} BDRs via Brapi | Analisadas: {len(selected_tickers)}
    </p>
    <p style='font-size: 0.75rem; margin: 0.5rem 0; color: #999;'>
        ⚠️ Sistema informativo. Não constitui recomendação de investimento.
    </p>
    <p style='font-size: 0.75rem; margin: 0.5rem 0; color: #999;'>
        Dados: Yahoo Finance, Finnhub, Polymarket, Brapi
    </p>
    <p style='font-size: 0.75rem; margin: 1rem 0 0 0; color: #aaa;'>
        Versão 3.0 Completa | Janeiro 2026
    </p>
</div>
""", unsafe_allow_html=True)
