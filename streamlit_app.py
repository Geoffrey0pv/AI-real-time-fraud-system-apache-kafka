"""
Aplicación Streamlit para el Sistema de Detección de Fraude en Tiempo Real

Esta aplicación web permite:
- Ingresar datos de transacciones manualmente
- Generar predicciones con múltiples modelos de ML
- Visualizar las probabilidades de fraude
- Comparar resultados entre diferentes algoritmos
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import logging
from prediction import load_models, process_transaction

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la página
st.set_page_config(
    page_title="🔒 Sistema de Detección de Fraude",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar la apariencia
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .fraud-alert {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 1rem;
        margin: 1rem 0;
    }
    .safe-alert {
        background-color: #e8f5e8;
        border-left: 5px solid #4caf50;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_ml_models():
    """Cargar modelos con cache para mejorar rendimiento"""
    try:
        return load_models()
    except Exception as e:
        st.error(f"Error al cargar los modelos: {str(e)}")
        return None

def create_sample_transaction():
    """Generar una transacción de ejemplo"""
    # Transacción normal (no fraudulenta)
    sample_normal = {
        'amount': 100.50,
        'time': 3600,
        **{f'v{i}': np.random.normal(0, 1) for i in range(1, 29)}
    }
    return sample_normal

def create_fraud_sample():
    """Generar una transacción fraudulenta de ejemplo"""
    # Transacción con características típicas de fraude
    sample_fraud = {
        'amount': 5000.00,  # Monto alto
        'time': 25200,      # Hora inusual (7 AM)
        **{f'v{i}': np.random.normal(0, 2) if i in [1, 3, 7, 10, 14] else np.random.normal(0, 0.5) 
           for i in range(1, 29)}
    }
    return sample_fraud

def plot_predictions(predictions):
    """Crear visualizaciones de las predicciones"""
    
    # Preparar datos para visualización
    models = list(predictions.keys())
    fraud_probs = []
    
    for model in models:
        if model == 'svc':
            fraud_probs.append(predictions[model]['fraud'])
        else:
            fraud_probs.append(predictions[model][1])  # Probabilidad de fraude
    
    # Gráfico de barras con probabilidades
    fig1 = go.Figure(data=[
        go.Bar(
            x=models,
            y=fraud_probs,
            text=[f'{prob:.3f}' for prob in fraud_probs],
            textposition='auto',
            marker_color=['#ff4444' if prob > 0.5 else '#44ff44' for prob in fraud_probs]
        )
    ])
    
    fig1.update_layout(
        title="Probabilidad de Fraude por Modelo",
        xaxis_title="Modelos",
        yaxis_title="Probabilidad de Fraude",
        yaxis=dict(range=[0, 1]),
        height=400
    )
    
    # Gráfico de gauge para el promedio
    avg_fraud_prob = np.mean(fraud_probs)
    
    fig2 = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = avg_fraud_prob,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Probabilidad Promedio de Fraude"},
        delta = {'reference': 0.5},
        gauge = {
            'axis': {'range': [None, 1]},
            'bar': {'color': "#ff4444" if avg_fraud_prob > 0.5 else "#44ff44"},
            'steps': [
                {'range': [0, 0.3], 'color': "lightgreen"},
                {'range': [0.3, 0.7], 'color': "yellow"},
                {'range': [0.7, 1], 'color': "lightcoral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 0.5
            }
        }
    ))
    
    fig2.update_layout(height=400)
    
    return fig1, fig2

def main():
    """Función principal de la aplicación"""
    
    # Título principal
    st.markdown('<h1 class="main-header">🔒 Sistema de Detección de Fraude</h1>', 
                unsafe_allow_html=True)
    
    # Descripción
    st.markdown("""
    ### 📊 Análisis de Transacciones con Machine Learning
    
    Esta aplicación utiliza **4 modelos de machine learning** entrenados para detectar 
    transacciones fraudulentas en tiempo real:
    
    - **Regresión Logística**: Modelo lineal robusto
    - **K-Vecinos**: Clasificación basada en similitud
    - **SVM**: Support Vector Machine para patrones complejos
    - **Árbol de Decisión**: Reglas interpretables
    """)
    
    # Cargar modelos
    models = load_ml_models()
    
    if models is None:
        st.error("❌ No se pudieron cargar los modelos. Verifica que los archivos .pkl estén en la carpeta 'model/'")
        return
    
    st.success(f"✅ {len(models)} modelos cargados correctamente")
    
    # Sidebar para configuración
    st.sidebar.header("⚙️ Configuración")
    
    # Opciones de entrada de datos
    data_input_method = st.sidebar.selectbox(
        "Método de entrada de datos:",
        ["Manual", "Ejemplo Normal", "Ejemplo Fraudulento", "JSON"]
    )
    
    # Contenedor principal dividido en columnas
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📝 Datos de la Transacción")
        
        transaction_data = {}
        
        if data_input_method == "Manual":
            # Campos principales
            amount = st.number_input("💰 Monto ($)", min_value=0.01, value=100.0, step=0.01)
            time = st.number_input("⏰ Tiempo (segundos desde medianoche)", 
                                 min_value=0, max_value=86400, value=3600)
            
            transaction_data['amount'] = amount
            transaction_data['time'] = time
            
            # Características V1-V28
            st.subheader("🔢 Características Anónimas (V1-V28)")
            
            # Usar tabs para organizar las variables
            tab1, tab2, tab3 = st.tabs(["V1-V10", "V11-V20", "V21-V28"])
            
            with tab1:
                for i in range(1, 11):
                    transaction_data[f'v{i}'] = st.number_input(
                        f"V{i}", value=0.0, step=0.01, format="%.3f"
                    )
            
            with tab2:
                for i in range(11, 21):
                    transaction_data[f'v{i}'] = st.number_input(
                        f"V{i}", value=0.0, step=0.01, format="%.3f"
                    )
            
            with tab3:
                for i in range(21, 29):
                    transaction_data[f'v{i}'] = st.number_input(
                        f"V{i}", value=0.0, step=0.01, format="%.3f"
                    )
        
        elif data_input_method == "Ejemplo Normal":
            transaction_data = create_sample_transaction()
            st.json(transaction_data)
            
        elif data_input_method == "Ejemplo Fraudulento":
            transaction_data = create_fraud_sample()
            st.json(transaction_data)
            
        elif data_input_method == "JSON":
            json_input = st.text_area(
                "Pega aquí los datos en formato JSON:",
                height=200,
                placeholder='{"amount": 100.5, "time": 3600, "v1": 0.123, ...}'
            )
            try:
                if json_input:
                    transaction_data = json.loads(json_input)
                    st.success("✅ JSON válido")
                else:
                    transaction_data = create_sample_transaction()
            except json.JSONDecodeError:
                st.error("❌ JSON inválido")
                transaction_data = create_sample_transaction()
    
    with col2:
        st.header("🎯 Resultados de Predicción")
        
        if st.button("🔍 Analizar Transacción", type="primary"):
            try:
                with st.spinner("Procesando transacción..."):
                    # Procesar transacción
                    predictions = process_transaction(transaction_data, models)
                    
                    # Mostrar métricas principales
                    fraud_probs = []
                    for model_name, pred in predictions.items():
                        if model_name == 'svc':
                            fraud_prob = pred['fraud']
                        else:
                            fraud_prob = pred[1]
                        fraud_probs.append(fraud_prob)
                    
                    avg_fraud_prob = np.mean(fraud_probs)
                    max_fraud_prob = np.max(fraud_probs)
                    
                    # Alerta principal
                    if avg_fraud_prob > 0.5:
                        st.markdown(f"""
                        <div class="fraud-alert">
                        <h3>🚨 ALERTA DE FRAUDE</h3>
                        <p><strong>Probabilidad promedio:</strong> {avg_fraud_prob:.1%}</p>
                        <p><strong>Probabilidad máxima:</strong> {max_fraud_prob:.1%}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="safe-alert">
                        <h3>✅ TRANSACCIÓN SEGURA</h3>
                        <p><strong>Probabilidad promedio:</strong> {avg_fraud_prob:.1%}</p>
                        <p><strong>Probabilidad máxima:</strong> {max_fraud_prob:.1%}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Métricas por modelo
                    st.subheader("📊 Resultados por Modelo")
                    
                    cols = st.columns(2)
                    model_names = ["Regresión Logística", "K-Vecinos", "SVM", "Árbol de Decisión"]
                    model_keys = ["logistic", "kneighbors", "svc", "tree"]
                    
                    for i, (display_name, key) in enumerate(zip(model_names, model_keys)):
                        with cols[i % 2]:
                            if key == 'svc':
                                fraud_prob = predictions[key]['fraud']
                                normal_prob = predictions[key]['non_fraud']
                            else:
                                normal_prob = predictions[key][0]
                                fraud_prob = predictions[key][1]
                            
                            st.metric(
                                label=display_name,
                                value=f"{fraud_prob:.1%}",
                                delta=f"Normal: {normal_prob:.1%}"
                            )
            
            except Exception as e:
                st.error(f"Error al procesar la transacción: {str(e)}")
    
    # Visualizaciones
    if st.button("📈 Generar Visualizaciones"):
        try:
            predictions = process_transaction(transaction_data, models)
            
            st.header("📈 Visualizaciones")
            
            # Crear gráficos
            fig1, fig2 = plot_predictions(predictions)
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
            
            # Tabla detallada
            st.subheader("📋 Tabla Detallada de Predicciones")
            
            results_df = []
            for model_name, pred in predictions.items():
                if model_name == 'svc':
                    normal_prob = pred['non_fraud']
                    fraud_prob = pred['fraud']
                else:
                    normal_prob = pred[0]
                    fraud_prob = pred[1]
                
                results_df.append({
                    'Modelo': model_name.replace('_', ' ').title(),
                    'Probabilidad Normal': f"{normal_prob:.4f}",
                    'Probabilidad Fraude': f"{fraud_prob:.4f}",
                    'Predicción': 'FRAUDE' if fraud_prob > 0.5 else 'NORMAL'
                })
            
            df = pd.DataFrame(results_df)
            st.dataframe(df, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error al generar visualizaciones: {str(e)}")
    
    # Información adicional en sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("ℹ️ Información")
    st.sidebar.markdown("""
    **Modelos utilizados:**
    - Regresión Logística
    - K-Nearest Neighbors  
    - Support Vector Machine
    - Árbol de Decisión
    
    **Umbral de detección:** 50%
    
    **Variables de entrada:** 30 características
    - Amount: Monto de la transacción
    - Time: Tiempo en segundos
    - V1-V28: Características anónimas PCA
    """)

if __name__ == "__main__":
    main()
