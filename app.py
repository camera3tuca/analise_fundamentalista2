"""
DASHBOARD PROFISSIONAL DE ANÁLISE DE BDRs - VERSÃO FINAL
Com mapeamento correto de tickers e filtros de validação
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
# CSS (mesmo de antes)
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
    }
    .alert-box {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid;
    }
    .alert-danger { background: #ffebee; border-color: #e74c3c; color: #c0392b; }
    .alert-info { background: #e3f2fd; border-color: #3498db; color: #2980b9; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# MAPEAMENTO CORRETO DE BDRs
# ============================================================

# Mapeamento manual dos principais BDRs com códigos especiais
TICKER_CORRECTIONS = {
    'GOGL': 'GOOGL',  # Google
    'AMZO': 'AMZN',   # Amazon
    'M1TA': 'META',   # Meta
    'NVDC': 'NVDA',   # Nvidia
    'MSCD': 'MSFT',   # Microsoft (alternativo)
    'T1SL': 'TSLA',   # Tesla (alternativo)
    'NTFL': 'NFLX',   # Netflix (alternativo)
    'APPL': 'AAPL',   # Apple (alternativo)
}

# Tickers conhecidos e válidos (lista curada)
KNOWN_VALID_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX',
    'AVGO', 'ASML', 'INTC', 'QCOM', 'ADBE', 'CSCO', 'ORCL', 'CRM',
    'V', 'MA', 'PYPL', 'JPM', 'BAC', 'GS', 'C', 'WFC', 'MS',
    'BABA', 'MELI', 'SHOP', 'DIS', 'SPOT', 'UBER', 'LYFT',
    'PFE', 'ABBV', 'JNJ', 'AMGN', 'MRNA', 'LLY', 'BMY',
    'NKE', 'SBUX', 'KO', 'PEP', 'WMT', 'COST', 'TGT', 'HD',
    'XOM', 'CVX', 'BP', 'SHEL', 'T', 'VZ', 'CMCSA',
    'BA', 'CAT', 'DE', 'HON', 'MMM', 'GE', 'LMT',
    'COIN', 'SQ', 'ABNB', 'DASH', 'SNOW', 'ZM', 'DOCU',
    'AMD', 'MU', 'LRCX', 'AMAT', 'KLAC', 'SNPS', 'CDNS',
    'NXPI', 'TXN', 'MRVL', 'QRVO', 'SWKS',
    'NOW', 'WDAY', 'PANW', 'CRWD', 'ZS', 'DDOG',
    'UNH', 'CVS', 'CI', 'HUM', 'ANTM', 'MCK', 'ABC',
    'AXP', 'BLK', 'SCHW', 'CME', 'ICE', 'SPGI', 'MCO',
    'NEE', 'DUK', 'SO', 'D', 'EXC', 'SRE', 'AEP',
    'UPS', 'FDX', 'NSC', 'UNP', 'CSX', 'JBHT',
    'MCD', 'CMG', 'YUM', 'QSR', 'DPZ', 'SBUX',
    'PG', 'UL', 'CL', 'KMB', 'CLX', 'CHD',
    'PM', 'MO', 'BTI',
    'MDLZ', 'KHC', 'GIS', 'K', 'CPB',
    'LOW', 'DHI', 'LEN', 'NVR', 'PHM',
    'F', 'GM', 'RIVN', 'LCID',
    'AAL', 'DAL', 'UAL', 'LUV', 'ALK',
    'MAR', 'HLT', 'IHG', 'H', 'WH',
    'BKNG', 'EXPE', 'TCOM', 'TRIP',
]

# API Keys
try:
    FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]
    BRAPI_API_TOKEN = st.secrets["BRAPI_API_TOKEN"]
except:
    FINNHUB_API_KEY = "d4uouchr01qnm7pnasq0d4uouchr01qnm7pnasqg"
    BRAPI_API_TOKEN = "iExnKM1xcbQcYL3cNPhPQ3"

# ============================================================
# FUNÇÃO MELHORADA PARA BUSCAR BDRs
# ============================================================

@st.cache_data(ttl=86400)
def get_all_bdrs_from_brapi():
    """
    Busca BDRs da B3 e valida tickers
    """
    try:
        url = f"https://brapi.dev/api/quote/list?token={BRAPI_API_TOKEN}"
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            # Fallback para lista conhecida
            return KNOWN_VALID_TICKERS, {}, []
        
        data = response.json()
        stocks = data.get('stocks', [])
        
        bdrs = []
        mapping = {}
        us_tickers = []
        
        for stock in stocks:
            ticker_br = stock.get('stock', '')
            name = stock.get('name', '')
            
            if ticker_br.endswith('34') or ticker_br.endswith('35'):
                # Extrair ticker base
                ticker_base = ticker_br[:-2]
                
                # Aplicar correções conhecidas
                ticker_us = TICKER_CORRECTIONS.get(ticker_base, ticker_base)
                
                # Validar se ticker parece válido (formato US)
                # Tickers US geralmente são 1-5 letras maiúsculas
                if (len(ticker_us) >= 1 and 
                    len(ticker_us) <= 5 and 
                    ticker_us.isalpha() and 
                    ticker_us.isupper()):
                    
                    # Se não está na lista conhecida, apenas adicionar se for comum
                    if ticker_us in KNOWN_VALID_TICKERS or len(ticker_us) <= 4:
                        bdrs.append({
                            'ticker_br': ticker_br,
                            'ticker_us': ticker_us,
                            'name': name,
                            'type': stock.get('type', 'stock')
                        })
                        
                        mapping[ticker_us] = ticker_br
                        us_tickers.append(ticker_us)
        
        # Remover duplicatas e ordenar
        us_tickers = sorted(list(set(us_tickers)))
        
        # Se encontrou poucos, usar lista conhecida
        if len(us_tickers) < 50:
            us_tickers = KNOWN_VALID_TICKERS
            mapping = {t: f"{t}34" for t in us_tickers}
        
        return us_tickers, mapping, bdrs
    
    except Exception as e:
        # Em caso de erro, usar lista conhecida
        return KNOWN_VALID_TICKERS, {t: f"{t}34" for t in KNOWN_VALID_TICKERS}, []

# ============================================================
# FUNÇÕES DE CACHE (Atualizadas)
# ============================================================

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
    """Busca dados fundamentalistas com validação rigorosa"""
    try:
        acao = yf.Ticker(ticker)
        info = acao.get_info()
        
        # Validação inicial
        if not info or len(info) < 5:
            return None
        
        market_cap = info.get('marketCap', 0)
        if not market_cap or market_cap <= 0:
            return None
        
        pe_ratio = info.get('forwardPE') or info.get('trailingPE')
        pb_ratio = info.get('priceToBook')
        div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        
        # ROE
        roe_medio = np.nan
        try:
            dre = acao.financials.T
            balanco = acao.balance_sheet.T
            
            if dre.empty or balanco.empty:
                return None
            
            roe_values = []
            for idx in range(min(3, len(dre))):
                try:
                    lucro = dre.iloc[idx].get('Net Income', np.nan)
                    pl = balanco.iloc[idx].get('Stockholders Equity', np.nan)
                    
                    if pd.notna(lucro) and pd.notna(pl) and pl != 0:
                        roe = (lucro / pl) * 100
                        if -100 < roe < 500:
                            roe_values.append(roe)
                except:
                    pass
            
            if roe_values:
                roe_medio = np.mean(roe_values)
            else:
                return None
        except:
            return None
        
        # Classificação
        if roe_medio >= 30:
            status, score = "🟢 Excelente", 95
        elif roe_medio >= 20:
            status, score = "🟢 Excelente", 85
        elif roe_medio >= 15:
            status, score = "🟡 Bom", 70
        elif roe_medio >= 10:
            status, score = "🟠 Atenção", 55
        else:
            status, score = "🔴 Fraco", 40
        
        if div_yield > 4:
            score += 5
        if pd.notna(pe_ratio) and pe_ratio > 50:
            score -= 5
        
        return {
            'ticker': ticker,
            'market_cap': market_cap / 1e9,
            'pe': pe_ratio if pd.notna(pe_ratio) else np.nan,
            'pb': pb_ratio if pd.notna(pb_ratio) else np.nan,
            'div_yield': div_yield,
            'roe': roe_medio,
            'status': status,
            'score': max(0, min(100, score)),
            'setor': info.get('sector', 'N/A'),
            'price': info.get('currentPrice', 0)
        }
    except Exception as e:
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
    """Salva no histórico"""
    try:
        if 'history' not in st.session_state:
            st.session_state.history = []
        
        st.session_state.history.append({
            'timestamp': datetime.now().isoformat(),
            'type': data_type,
            'data': data
        })
        
        if len(st.session_state.history) > 100:
            st.session_state.history = st.session_state.history[-100:]
        
        return True
    except:
        return False

def get_recommendations(df):
    """Gera recomendações"""
    recommendations = []
    
    # Value
    good_value = df[(df['roe'] > 20) & (df['pe'] < 20)]
    if not good_value.empty:
        recommendations.append({
            'tipo': '💎 Value',
            'tickers': good_value.nlargest(3, 'roe')['ticker'].tolist(),
            'razao': 'Alto ROE com P/E atrativo',
            'cor': 'success'
        })
    
    # Dividendos
    high_div = df[df['div_yield'] > 4].nlargest(3, 'div_yield')
    if not high_div.empty:
        recommendations.append({
            'tipo': '💰 Dividendos',
            'tickers': high_div['ticker'].tolist(),
            'razao': 'Dividend Yield > 4%',
            'cor': 'info'
        })
    
    # Growth
    growth = df[(df['roe'] > 25) & (df['pe'] > 30)]
    if not growth.empty:
        recommendations.append({
            'tipo': '🚀 Growth',
            'tickers': growth.nlargest(3, 'roe')['ticker'].tolist(),
            'razao': 'Alto crescimento',
            'cor': 'warning'
        })
    
    return recommendations

def create_excel_download(dfs_dict):
    """Cria Excel"""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for sheet_name, df in dfs_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()

def create_correlation_heatmap(df):
    """Cria heatmap"""
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
    
    fig.update_layout(title='Matriz de Correlação', height=500)
    return fig

# ============================================================
# BUSCAR BDRs
# ============================================================

ALL_US_TICKERS, TICKER_MAPPING, ALL_BDRS_INFO = get_all_bdrs_from_brapi()

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## ⚙️ Configurações")

if ALL_US_TICKERS:
    st.sidebar.success(f"📊 **{len(ALL_US_TICKERS)} BDRs** validadas")
else:
    st.sidebar.warning("⚠️ Usando lista padrão")

# Tipo de análise
analysis_type = st.sidebar.radio(
    "Tipo de Análise",
    ["📊 Dashboard Completo", "📰 Notícias", "💼 Fundamentos", 
     "🎯 Polymarket", "🔍 Comparador", "📋 Lista BDRs"],
    key="analysis_type"
)

# Seleção
st.sidebar.markdown("### 📋 Seleção")

if ALL_US_TICKERS:
    selection_mode = st.sidebar.radio(
        "Modo",
        ["🎯 Top 50", "📊 Top 100", "✏️ Personalizado"],
        key="selection_mode"
    )
    
    if selection_mode == "🎯 Top 50":
        selected_tickers = ALL_US_TICKERS[:50]
    elif selection_mode == "📊 Top 100":
        selected_tickers = ALL_US_TICKERS[:100]
    else:
        selected_tickers = st.sidebar.multiselect(
            "Selecione",
            ALL_US_TICKERS,
            default=ALL_US_TICKERS[:20],
            key="custom_tickers"
        )
else:
    selected_tickers = KNOWN_VALID_TICKERS[:50]

# Filtros
st.sidebar.markdown("### 🎛️ Filtros")

with st.sidebar.expander("💼 Fundamentais"):
    roe_range = st.slider("ROE (%)", 0.0, 200.0, (0.0, 200.0))
    pe_range = st.slider("P/E", 0.0, 100.0, (0.0, 100.0))
    div_yield_min = st.slider("Div Yield Mín (%)", 0.0, 10.0, 0.0)
    market_cap_min = st.number_input("Market Cap Mín (B)", 0.0, 5000.0, 0.0)

with st.sidebar.expander("📊 Análise"):
    min_score = st.slider("Score Mínimo", 0, 100, 20)

# Alertas
st.sidebar.markdown("### 🔔 Alertas")
with st.sidebar.expander("Configurar"):
    alert_score = st.slider("Alerta Score ≥", 0, 100, 80)
    alert_roe = st.slider("Alerta ROE ≥ (%)", 0, 100, 25)

# Visual
st.sidebar.markdown("### 🎨 Visual")
with st.sidebar.expander("Layout"):
    show_charts = st.checkbox("Gráficos", True)

# Botões
st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🔄 Atualizar", type="primary"):
        st.cache_data.clear()
        st.rerun()

# Info
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Ativos:** {len(selected_tickers)}")
st.sidebar.markdown(f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_")

# ============================================================
# HEADER
# ============================================================

st.markdown('<h1 class="main-header">📊 Dashboard Completo de BDRs</h1>', 
            unsafe_allow_html=True)

if ALL_US_TICKERS:
    st.info(f"""
    🎉 **{len(selected_tickers)} de {len(ALL_US_TICKERS)} BDRs validadas** | 
    Dados em tempo real via Yahoo Finance, Finnhub e Polymarket
    """)

# ============================================================
# LISTA DE BDRs
# ============================================================

if analysis_type == "📋 Lista BDRs":
    st.subheader("📋 Lista de BDRs Validadas")
    
    if ALL_BDRS_INFO:
        df_bdrs = pd.DataFrame(ALL_BDRS_INFO)
        
        col1, col2 = st.columns(2)
        col1.metric("Total", len(df_bdrs))
        col2.metric("Nível 1 (34)", len(df_bdrs[df_bdrs['ticker_br'].str.endswith('34')]))
        
        st.dataframe(df_bdrs, width=None, hide_index=True)
        
        csv = df_bdrs.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Lista (CSV)",
            csv,
            f"bdrs_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
    elif KNOWN_VALID_TICKERS:
        st.success(f"✅ Usando lista curada de {len(KNOWN_VALID_TICKERS)} BDRs conhecidas")
        
        df_known = pd.DataFrame({
            'ticker_us': KNOWN_VALID_TICKERS,
            'ticker_br': [f"{t}34" for t in KNOWN_VALID_TICKERS]
        })
        
        st.dataframe(df_known, width=None, hide_index=True)

# ============================================================
# DASHBOARD COMPLETO
# ============================================================

elif analysis_type == "📊 Dashboard Completo":
    
    if not selected_tickers:
        st.warning("⚠️ Selecione tickers no sidebar")
        st.stop()
    
    # Progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Notícias
    status_text.text(f"📰 Analisando notícias de {len(selected_tickers)} BDRs...")
    progress_bar.progress(10)
    
    news_opps = []
    news_limit = min(30, len(selected_tickers))  # Reduzido para evitar timeout
    
    for i, ticker in enumerate(selected_tickers[:news_limit]):
        news = get_news_data(ticker)
        
        if news:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                score = 50
                events = []
                priority = "🟡 Média"
                
                # Earnings
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
                
                # Dividendos
                if info.get('dividendYield') and info.get('dividendYield') > 0:
                    div_yield = info.get('dividendYield') * 100
                    score += 15
                    events.append(f"Div: {div_yield:.2f}%")
                
                if len(news) > 5:
                    score += 10
                    events.append(f"{len(news)} notícias")
                
                if events or score > 60:
                    news_opps.append({
                        'ticker': ticker,
                        'bdr': TICKER_MAPPING.get(ticker, f"{ticker}34"),
                        'score': score,
                        'priority': priority,
                        'events': ', '.join(events) if events else 'Notícias'
                    })
            except:
                pass
        
        time.sleep(0.1)
        progress_bar.progress(10 + int((i / news_limit) * 30))
    
    # Fundamentos
    status_text.text(f"💼 Analisando fundamentos...")
    progress_bar.progress(45)
    
    fund_data = []
    fund_limit = min(50, len(selected_tickers))  # Reduzido
    
    total_tentativas = sem_dados = filtrados = 0
    
    for i, ticker in enumerate(selected_tickers[:fund_limit]):
        total_tentativas += 1
        data = get_fundamental_data(ticker)
        
        if data:
            if (roe_range[0] <= data.get('roe', 0) <= roe_range[1] and
                pe_range[0] <= data.get('pe', 0) <= pe_range[1] and
                data.get('div_yield', 0) >= div_yield_min and
                data.get('market_cap', 0) >= market_cap_min):
                fund_data.append(data)
            else:
                filtrados += 1
        else:
            sem_dados += 1
        
        time.sleep(0.05)
        progress_bar.progress(45 + int((i / fund_limit) * 45))
    
    # Polymarket
    status_text.text("🎯 Polymarket...")
    poly_markets = get_polymarket_data()
    
    progress_bar.progress(100)
    status_text.text("✅ Concluído!")
    time.sleep(0.3)
    progress_bar.empty()
    status_text.empty()
    
    # Stats debug
    with st.expander("ℹ️ Estatísticas"):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tentativas", total_tentativas)
        col2.metric("Com Dados", total_tentativas - sem_dados)
        col3.metric("Filtrados", filtrados)
        col4.metric("Final", len(fund_data))
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='margin:0; font-size:0.9rem;'>📊 Analisadas</h3>
            <h1 style='margin:10px 0; font-size:2.5rem;'>{len(selected_tickers)}</h1>
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>BDRs</p>
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
            <h3 style='margin:0; font-size:0.9rem;'>💼 Fundamentos</h3>
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
            <p style='margin:0; font-size:0.8rem; opacity:0.9;'>retorno/capital</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Alertas
    if fund_data:
        df_fund = pd.DataFrame(fund_data)
        
        high_score = df_fund[df_fund['score'] >= alert_score]
        if not high_score.empty:
            tickers_list = ', '.join(high_score['ticker'].tolist()[:8])
            if len(high_score) > 8:
                tickers_list += f" +{len(high_score)-8}"
            
            st.markdown(f"""
            <div class='alert-box alert-danger'>
                <strong>🚨 {len(high_score)} ALERTAS!</strong><br>
                Score ≥ {alert_score}: {tickers_list}
            </div>
            """, unsafe_allow_html=True)
        
        high_roe = df_fund[df_fund['roe'] >= alert_roe]
        if not high_roe.empty:
            tickers_list = ', '.join(high_roe['ticker'].tolist()[:8])
            if len(high_roe) > 8:
                tickers_list += f" +{len(high_roe)-8}"
            
            st.markdown(f"""
            <div class='alert-box alert-info'>
                <strong>💎 {len(high_roe)} ROE Excepcional!</strong><br>
                ROE ≥ {alert_roe}%: {tickers_list}
            </div>
            """, unsafe_allow_html=True)
    
    # Recomendações
    if fund_data:
        st.markdown("### 🤖 Recomendações")
        
        recommendations = get_recommendations(df_fund)
        
        if recommendations:
            cols = st.columns(min(len(recommendations), 4))
            
            for i, rec in enumerate(recommendations[:4]):
                with cols[i]:
                    tickers_str = ', '.join(rec['tickers'][:3])
                    if len(rec['tickers']) > 3:
                        tickers_str += f" +{len(rec['tickers'])-3}"
                    
                    st.markdown(f"""
                    <div style='background: #f8f9fa; padding: 1rem; border-radius: 10px; 
                                border-left: 4px solid {"#27ae60" if rec["cor"] == "success" else "#3498db"};'>
                        <h4 style='margin: 0 0 0.5rem 0;'>{rec['tipo']}</h4>
                        <p style='margin: 0; font-size: 0.9rem;'><strong>{tickers_str}</strong></p>
                        <p style='margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666;'>{rec['razao']}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📰 Notícias", "💼 Fundamentos", "📊 Gráficos", "📥 Exportar"])
    
    with tab1:
        st.subheader(f"📰 {len(news_opps)} Oportunidades")
        
        if news_opps:
            df_news = pd.DataFrame(news_opps).sort_values('score', ascending=False)
            
            if 'priority' in df_news.columns:
                col1, col2, col3 = st.columns(3)
                urgentes = len(df_news[df_news['priority'] == '🔴 Urgente'])
                altas = len(df_news[df_news['priority'] == '🟠 Alta'])
                medias = len(df_news[df_news['priority'] == '🟡 Média'])
                
                col1.metric("🔴 Urgentes", urgentes)
                col2.metric("🟠 Altas", altas)
                col3.metric("🟡 Médias", medias)
            
            st.dataframe(df_news, width=None, hide_index=True)
        else:
            st.info("📭 Nenhuma notícia relevante")
    
    with tab2:
        st.subheader(f"💼 {len(fund_data)} Empresas")
        
        if fund_data:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("ROE Médio", f"{df_fund['roe'].mean():.1f}%")
            col2.metric("P/E Médio", f"{df_fund['pe'].mean():.1f}")
            col3.metric("Div Yield", f"{df_fund['div_yield'].mean():.2f}%")
            col4.metric("Excelentes", excelentes)
            
            st.dataframe(
                df_fund.sort_values('score', ascending=False),
                width=None,
                hide_index=True
            )
        else:
            st.info("📊 Sem dados")
    
    with tab3:
        if show_charts and fund_data:
            # Top 15
            fig1 = px.bar(
                df_fund.nlargest(15, 'score'),
                x='ticker',
                y='score',
                color='status',
                title=f'Top 15 por Score',
                color_discrete_map={
                    '🟢 Excelente': '#27ae60',
                    '🟡 Bom': '#f39c12',
                    '🟠 Atenção': '#e67e22',
                    '🔴 Fraco': '#e74c3c'
                }
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # ROE vs P/E
            fig2 = px.scatter(
                df_fund,
                x='pe',
                y='roe',
                size='market_cap',
                color='status',
                hover_data=['ticker'],
                title='ROE vs P/E'
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Heatmap
            corr_fig = create_correlation_heatmap(df_fund)
            if corr_fig:
                st.plotly_chart(corr_fig, use_container_width=True)
    
    with tab4:
        st.subheader("📥 Exportar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if fund_data:
                csv = df_fund.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "💼 Fundamentos (CSV)",
                    csv,
                    f"fundamentos_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
        
        with col2:
            if news_opps and fund_data:
                excel = create_excel_download({
                    'Notícias': pd.DataFrame(news_opps),
                    'Fundamentos': df_fund,
                    'Resumo': pd.DataFrame([{
                        'Total_BDRs': len(ALL_US_TICKERS),
                        'Analisadas': len(selected_tickers),
                        'Fundamentos': len(fund_data),
                        'ROE_Medio': df_fund['roe'].mean(),
                        'Data': datetime.now().strftime('%Y-%m-%d %H:%M')
                    }])
                })
                
                st.download_button(
                    "📊 Completo (Excel)",
                    excel,
                    f"analise_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    "application/vnd.ms-excel"
                )

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 1rem 0;'>
    <p style='font-size: 0.85rem; margin: 0;'>
        <strong>Dashboard BDRs da B3</strong> | 
        Base: {len(ALL_US_TICKERS)} BDRs validadas | 
        Analisadas: {len(selected_tickers)}
    </p>
    <p style='font-size: 0.75rem; margin: 0.5rem 0; color: #999;'>
        ⚠️ Sistema informativo. Não constitui recomendação de investimento.
    </p>
    <p style='font-size: 0.75rem; margin: 0; color: #aaa;'>
        Versão 4.0 Final | Fevereiro 2026
    </p>
</div>
""", unsafe_allow_html=True)
