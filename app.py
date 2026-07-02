import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="Dashboard Mercado de Combustibles")

@st.cache_data
def cargar_datos_resumen():
    p_anual = pd.read_csv('../datasets/bencina_limpia/resumenes/precio_anual.csv')
    df_rel = pd.read_csv('../datasets/bencina_limpia/resumenes/df_relacion.csv')
    p_mensual = pd.read_csv('../datasets/bencina_limpia/resumenes/patron_mensual.csv')
    p_region = pd.read_csv('../datasets/bencina_limpia/resumenes/precio_region.csv')
    p_dist = pd.read_csv('../datasets/bencina_limpia/resumenes/precio_dist.csv')
    comp = pd.read_csv('../datasets/bencina_limpia/resumenes/composicion.csv')
    p_decil = pd.read_csv('../datasets/casen_limpia/ingreso_percapita_decil.csv')
    return p_anual, df_rel, p_mensual, p_region, p_dist, comp, p_decil

@st.cache_data
def cargar_datos_mapa():
    df_bencinas = pd.read_parquet('../datasets/bencina_limpia/bencinas_rm_completo.parquet')
    comunas_geo = gpd.read_file('../datasets/DPA_2023/COMUNAS/COMUNAS_v1.shp')
    comunas_rm = comunas_geo[comunas_geo['CUT_REG'] == '13'].copy()
    comunas_rm = comunas_rm.to_crs(epsg=4326)
    
    ingreso_region = pd.read_csv('../datasets/casen_limpia/ingreso_region.csv')
    ingreso_2024 = ingreso_region[
        (ingreso_region['anio'] == 2024) & 
        (ingreso_region['tipo_ingreso'] == 'Ingreso autónomo') & 
        (ingreso_region['region'] != 'Total')
    ].copy()
    
    return df_bencinas, comunas_rm, comunas_rm.__geo_interface__, ingreso_2024

p_anual, df_rel, p_mensual, p_region, p_dist, comp, p_decil = cargar_datos_resumen()
df_bencinas, comunas_rm, geojson_rm, ingreso_2024 = cargar_datos_mapa()

# BARRA DE NAVEGACIÓN LATERAL
st.sidebar.title("Navegación del Proyecto")
seccion = st.sidebar.radio(
    "Selecciona el análisis:",
    [
        "1. Evolución y Eventos Geopolíticos",
        "2. Estacionalidad Mensual",
        "3. Regiones y Distribuidoras",
        "4. CASEN vs Precios Nacionales",
        "5. Mapa RM y Alzas",
        "6. Desigualdad y Esfuerzo Económico"
    ]
)
if seccion == "1. Evolución y Eventos Geopolíticos":
    st.title("¿Qué eventos explican las alzas de precios?")
    
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(go.Scatter(x=df_rel['anio'], y=df_rel['precio_promedio'], mode='lines+markers', name='Gasolina 93 (CLP)', line=dict(color='#e74c3c')), secondary_y=False)
    fig.add_trace(go.Scatter(x=df_rel['anio'], y=df_rel['dolar_promedio'], mode='lines+markers', name='Dólar (CLP)', line=dict(color='#2ecc71')), secondary_y=True)
    
    fig.add_vline(x=2022, line_dash='dash', line_color='orange', annotation_text='Guerra Rusia-Ucrania', annotation_position='top left')
    fig.add_vline(x=2023, line_dash='dash', line_color='purple', annotation_text='Israel-Hamas', annotation_position='top right')
    fig.add_vline(x=2014, line_dash='dash', line_color='steelblue', annotation_text='Caída petróleo', annotation_position='top right')
    
    fig.update_layout(height=500)
    fig.update_yaxes(title_text='Precio Gasolina 93 (CLP)', secondary_y=False)
    fig.update_yaxes(title_text='Valor Dólar (CLP)', secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)

elif seccion == "2. Estacionalidad Mensual":
    st.title("¿Existen patrones mensuales en los precios?")
    
    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    p_mensual['mes_nombre'] = p_mensual['mes'].apply(lambda x: meses_nombres[x-1])
    
    fig = go.Figure(go.Bar(
        x=p_mensual['mes_nombre'],
        y=p_mensual['precio_normalizado'],
        marker_color=['#e74c3c' if v > 1 else '#2ecc71' for v in p_mensual['precio_normalizado']],
        text=p_mensual['precio_normalizado'].round(2),
        textposition='outside'
    ))
    fig.add_hline(y=1, line_dash='dash', line_color='gray', annotation_text='Promedio anual')
    fig.update_layout(yaxis_title='Precio relativo al promedio', height=500)
    
    st.plotly_chart(fig, use_container_width=True)

elif seccion == "3. Regiones y Distribuidoras":
    st.title("¿Existen diferencias sistemáticas por marca o zona?")
    col1, col2 = st.columns(2)
    
    with col1:
        fig2 = go.Figure(go.Bar(
            x=p_dist['precio'], y=p_dist['distribuidor_limpio'], orientation='h', marker_color='steelblue',
            text=p_dist['precio'].round(0), textposition='outside'
        ))
        fig2.update_layout(title='Precio promedio por marca', xaxis_title='Precio (CLP)', height=400)
        st.plotly_chart(fig2, use_container_width=True)
        
    st.divider()
    st.subheader("Composición del Mercado por Región")
    orden = comp[comp['tipo_distribuidor'] == 'Grande'].sort_values('porcentaje', ascending=True)['region_limpia']
    fig3 = go.Figure()
    colores = {'Grande': '#2ecc71', 'Sin Bandera': '#e74c3c', 'Independiente': '#f39c12'}
    
    for tipo in ['Grande', 'Sin Bandera', 'Independiente']:
        df_tipo = comp[comp['tipo_distribuidor'] == tipo].set_index('region_limpia')
        fig3.add_trace(go.Bar(
            y=orden,
            x=[df_tipo.loc[r, 'porcentaje'] if r in df_tipo.index else 0 for r in orden],
            name=tipo, orientation='h', marker_color=colores[tipo]
        ))
    fig3.update_layout(barmode='stack', xaxis_title='Porcentaje (%)', height=500)
    st.plotly_chart(fig3, use_container_width=True)

elif seccion == "4. CASEN vs Precios Nacionales":
    st.title("Nivel Socioeconómico y Precios (Datos CASEN)")
    anio_scatter = st.radio("Año de análisis (Precios):", (2024, 2026), horizontal=True)
    
    precio_reg = df_bencinas[(df_bencinas['anio'] == anio_scatter) & (df_bencinas['combustible_limpio'] == 'Gasolina 93')].groupby('region_limpia')['precio'].mean().reset_index()
    precio_reg.columns = ['region', 'precio_promedio']
    precio_reg['region'] = precio_reg['region'].replace('Araucanía', 'La Araucanía')
    
    df_cruce = pd.merge(ingreso_2024, precio_reg, on='region')
    df_cruce['ingreso_miles'] = df_cruce['ingreso_real_nov2024'] / 1000
    
    fig_scatter = go.Figure(go.Scatter(
        x=df_cruce['ingreso_miles'], y=df_cruce['precio_promedio'], mode='markers+text',
        text=df_cruce['region'], textposition='top center', marker=dict(size=12, color='steelblue')
    ))
    fig_scatter.update_layout(xaxis_title='Ingreso Autónomo Promedio (miles de CLP)', yaxis_title=f'Precio Gasolina 93 ({anio_scatter})', height=550)
    st.plotly_chart(fig_scatter, use_container_width=True)

elif seccion == "5. Mapa RM y Alzas":
    st.title("Dinámica Espacial y Absorción de Alzas (RM)")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        modo_mapa = st.radio("Visualización:", ("Precio Absoluto por Año", "Alza de Precio (2024 → 2026)"))
        if modo_mapa == "Precio Absoluto por Año":
            anio_mapa = st.slider("Año:", 2012, 2026, 2024)
        else:
            st.info("Muestra el aumento exacto que absorbió cada bencinera en la crisis.")

    fig_mapa = px.choropleth_mapbox(
        comunas_rm, geojson=geojson_rm, locations=comunas_rm.index, hover_name='COMUNA',
        mapbox_style='carto-positron', zoom=9, center={'lat': -33.45, 'lon': -70.65}, opacity=0.1
    )

    if modo_mapa == "Precio Absoluto por Año":
        df_p = df_bencinas[(df_bencinas['anio'] == anio_mapa) & (df_bencinas['combustible_limpio'] == 'Gasolina 93') & (df_bencinas['region_limpia'] == 'Metropolitana')].dropna(subset=['latitud', 'longitud'])
        vmin, vmax = df_p['precio'].quantile(0.01), df_p['precio'].quantile(0.99)
        color_col, colorscale, titulo_legend, hover = 'precio', 'YlOrRd', 'Precio (CLP)', df_p['precio'].round(0).astype(str) + ' CLP'
    else:
        df_rm_fil = df_bencinas[(df_bencinas['region_limpia'] == 'Metropolitana') & (df_bencinas['combustible_limpio'] == 'Gasolina 93')]
        df_24 = df_rm_fil[df_rm_fil['anio'] == 2024][['id', 'latitud', 'longitud', 'precio']].drop_duplicates('id')
        df_26 = df_rm_fil[df_rm_fil['anio'] == 2026][['id', 'precio']].drop_duplicates('id')
        df_p = pd.merge(df_24, df_26, on='id', suffixes=('_2024', '_2026'))
        df_p['alza'] = df_p['precio_2026'] - df_p['precio_2024']
        df_p = df_p.dropna(subset=['latitud', 'longitud'])
        vmin, vmax = df_p['alza'].quantile(0.01), df_p['alza'].quantile(0.99)
        color_col, colorscale, titulo_legend, hover = 'alza', 'Reds', 'Alza (CLP)', 'Subió: ' + df_p['alza'].round(0).astype(str) + ' CLP'

    fig_mapa.add_scattermapbox(
        lat=df_p['latitud'], lon=df_p['longitud'], mode='markers', text=hover, name='Bencineras',
        marker=dict(size=8, color=df_p[color_col], colorscale=colorscale, cmin=vmin, cmax=vmax, showscale=True, colorbar=dict(title=titulo_legend, x=1.05))
    )
    fig_mapa.update_layout(height=650, margin={"r":0,"t":30,"l":0,"b":0})
    
    with col2:
        st.plotly_chart(fig_mapa, use_container_width=True)
        
elif seccion == "6. Desigualdad y Esfuerzo Económico":
    st.title("Brecha de Asequibilidad: ¿A quién le duele más llenar el estanque?")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        precio_nac_2024 = p_anual[(p_anual['anio'] == 2024) & (p_anual['combustible_limpio'] == 'Gasolina 93')]['precio'].mean()
        costo_estanque = precio_nac_2024 * 40
        
        df_decil = p_decil[(p_decil['anio'] == 2024) & (p_decil['decil'] != 'Total')].copy()
        
        orden_deciles = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
        df_decil['decil'] = pd.Categorical(df_decil['decil'], categories=orden_deciles, ordered=True)
        df_decil = df_decil.sort_values('decil')
        df_decil['esfuerzo_pct'] = (costo_estanque / df_decil['ingreso_percapita_media']) * 100
        
        fig_decil = go.Figure()
        
        fig_decil.add_trace(go.Bar(
            x=df_decil['decil'],
            y=df_decil['esfuerzo_pct'],
            marker_color=px.colors.sequential.Reds[::-1],
            text=df_decil['esfuerzo_pct'].round(1).astype(str) + '%',
            textposition='outside',
            name='% del Ingreso'
        ))
        
        fig_decil.update_layout(
            title=f'Costo de llenar un estanque de 40L como % del Ingreso Per Cápita (2024)',
            xaxis_title='Decil de Ingreso (I = Más pobre, X = Más rico)',
            yaxis_title='% del Ingreso Per Cápita',
            height=500
        )
        
        st.plotly_chart(fig_decil, use_container_width=True)