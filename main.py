import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------------------------------------------------------
# I. Carreguem i preparem les dades
# ------------------------------------------------------------------------------

# Configurem l'amplada de la pàgina a 'wide' per aprofitar tot l'espai de la pantalla
st.set_page_config(page_title="Esport i Societat a Catalunya", layout="wide")

# Utilitzem @st.cache_data perquè Streamlit guardi el resultat en memòria cache.
# Amb això evitem recarregar fitxers CSV cada vegada que l'usuari filtra les dades.
@st.cache_data
def load_data():
    """
    Funció encarregada d'extreure, transformar i carregar les dades.
    """
    # I.I. Carreguem CSV
    # Càrrega del Cens d'Equipaments de Catalunya
    df_esports = pd.read_csv(
        "Instal·lacions_censades_al_Cens_d’Equipaments_Esportius_de_Catalunya_(CEEC)_20260528.csv",
        sep=",",
        decimal=","
    )
    # Càrrega dades macroeconòmiques d'Idescat
    df_pib = pd.read_csv(
        "pibc21925com.csv",
        sep=";",
        decimal=","
    )

    # I.II Netegem i filtrem
    # Seleccionem l'any 2021, ja que són dades definitives
    # L'Idescat indica dades provisionals amb estat=p
    condicio_any = df_pib['any'] == 2021

    # Filtrem per l'índex base 100 de Catalunya
    # Permet comparar les comarques proporcionalment
    condicio_concepte = df_pib['concepte'].str.contains(
        "PIB per habitant (índex Catalunya=100)",
        regex=False,
        na=False)

    # Dataset PIB 2021
    df_pib_2021 = df_pib[condicio_any & condicio_concepte].copy()

    # Eliminem concepte (és el tipus de PIB) i estat (indica si es provisional)
    df_pib_2021 = df_pib_2021.drop(columns=['concepte', 'estat'])

    # I.III Integració de les dades
    # Fusionem el dataframe geogràfic d'esports amb l'econòmic
    # Utilitzem la comarca com a clau d'unió
    # Fem un 'left' join per mantenir totes les instal·lacions esportives encara que falti el PIB
    df_merged = pd.merge(df_esports,
                         df_pib_2021,
                         left_on="Comarca",
                         right_on="comarca o Aran",
                         how="left")

    # Netegem la columna duplicada del dataset de l'Idescat
    df_merged = df_merged.drop(columns=['comarca o Aran'])

    return df_merged

# Executem la càrrega
df = load_data()

# I.IV Neteja de valors nuls
# Eliminem instal·lacions on no hi ha la dada econòmica
df = df.dropna(subset=['any', 'valor'])

# Creem diccionari global per traduir els codis tècnics del CEEC
dict_esports = {
    'PAD': 'Pàdel',
    'PAL': 'Piscina',
    'PET': 'Petanca',
    'TEN': 'Tennis',
    'PAV': 'Pavelló',
    'CAM': 'Camp Futbol'
}

# ------------------------------------------------------------------------------
# II. Interfície web amb StreamLit
# ------------------------------------------------------------------------------
st.title("L'Esport a Catalunya: Un reflex socioeconòmic?")
st.markdown("""
En aquesta plataforma visual analitzem les instal·lacions esportives de Catalunya creuades amb els indicadors de riquesa municipal de l'IDESCAT (2021).
Explorem la infraestructura a través dels filtres interactius per descobrir la relació entre l'esport i l'economia.
""")

# Creem 4 pestanyes
tab1, tab2, tab3, tab4 = st.tabs([
    "Geolocalització",
    "Anàlisi territorial",
    "Visió de conjunt",
    "Impacte econòmic (PIB)"
])

# ------------------------------------------------------------------------------
# Pestanya 1: mapa interactiu
# ------------------------------------------------------------------------------
with tab1:
    st.header("Distribució territorial de les instal·lacions esportives")

    col1, col2 = st.columns(2)
    with col1:
        sel_comarca_map = st.selectbox("Filtra el mapa per comarca",
                                       ["Totes"] + list(df['Comarca'].unique()),
                                       key="map_com")
    with col2:
        sel_tit_map = st.selectbox("Filtra el mapa per titularitat",
                                   ["Totes"] + list(df['Titularitat'].unique()),
                                   key="map_tit")

    df_map = df.copy()
    if sel_comarca_map != "Totes":
        df_map = df_map[df_map['Comarca'] == sel_comarca_map]
    if sel_tit_map != "Totes":
        df_map = df_map[df_map['Titularitat'] == sel_tit_map]

    # Tipus: Mapa de punts (scatter map)
    # Geolocalitzem cada instal·lació per veure la seva dispersió sobre el territori català
    fig_map = px.scatter_map(
        df_map, lat="Latitud", lon="Longitud", color="Titularitat",
        hover_name="Municipi", hover_data=["Tipus propietat"],
        color_discrete_sequence=px.colors.qualitative.Safe,
        zoom=7, height=450, title=f"Mostrant {len(df_map)} recintes geolocalitzats"
        )
    fig_map.update_layout(map_style="open-street-map", margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig_map, width='stretch')

# ------------------------------------------------------------------------------
# Pestanya 2: breu anàlisis territorial
# ------------------------------------------------------------------------------
with tab2:
    st.header("Nombre i estructura de l'esport per comarques")

    st.subheader("Gràfic 1: Rànquing de comarques")
    df_ranking = df['Comarca'].value_counts().head(15).reset_index()
    df_ranking.columns = ['Comarca', 'Instal·lacions']

    # Tipus: Gràfic de barres horitzontal
    # Identifiquem fàcilment quines són les comarques amb major densitat d'infraestructures
    fig_g1 = px.bar(
        df_ranking, x='Instal·lacions', y='Comarca', orientation='h',
        color='Instal·lacions', color_continuous_scale='Blues',
        title="Top 15 comarques amb més recintes esportius",
        height=475
    )
    fig_g1.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_g1, width='stretch')

    st.markdown("---")

    st.subheader("Gràfic 2: Titularitat, públic vs privat")
    df_tit_com = df.groupby(['Comarca', 'Titularitat']).size().reset_index(name='Count')

    # Tipus: Gràfic de barres apilat
    # Comparem el model de gestió (públic vs privat) i el seu pes en cada comarca
    fig_g2 = px.bar(
        df_tit_com, x='Comarca', y='Count', color='Titularitat',
        title="Distribució de la titularitat per comarca, segons nombre",
        color_discrete_sequence=px.colors.qualitative.Set2,
        height=700
    )
    fig_g2.update_layout(xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig_g2, width='stretch')

# ------------------------------------------------------------------------------
# Pestanya 3: Visió de conjunt
# ------------------------------------------------------------------------------
with tab3:
    st.header("Totes les comarques en un sol cop d'ull")
    st.markdown("""
    Aquestes dues visualitzacions ens permeten avaluar de forma simultània l'equilibri de gestió i la proporció a tot Catalunya.
    """)

    st.subheader("Gràfic 3: Accés territorial, estructura relativa al 100%")
    df_tit_com_all = df.groupby(['Comarca', 'Titularitat']).size().reset_index(name='Total')

    # Tipus: Gràfic de barres apilat al 100%
    # Eliminem l'efecte del volum total per analitzar la proporció relativa de cada model de titularitat
    fig_g3 = px.bar(
        df_tit_com_all, x='Comarca', y='Total', color='Titularitat',
        title="Percentatge relatiu del model de propietat segons comarca",
        color_discrete_sequence=px.colors.qualitative.Set2,
        height=650
    )

    fig_g3.update_traces(marker_line_width=0)
    fig_g3.update_layout(
        barmode='stack',
        barnorm='percent',
        xaxis={'categoryorder':'total descending'},
        yaxis_title="Percentatge (%)"
    )
    st.plotly_chart(fig_g3, width='stretch')

    st.markdown("---")

    st.subheader("Gràfic 4: Mapa de Calor Estructural (Treemap de la Catalunya Esportiva)")

    # Pivotem les dades per fondre (melt) els esports seleccionats en una estructura de rànquing macro
    df_esports_melt = df.melt(
        id_vars=['Comarca'],
        value_vars=list(dict_esports.keys()),
        var_name='CodiEsport', value_name='Instal·lacions'
    )
    df_esports_melt['Esport'] = df_esports_melt['CodiEsport'].map(dict_esports)
    df_esports_grouped = df_esports_melt.groupby(['Comarca', 'Esport'])['Instal·lacions'].sum().reset_index()
    df_esports_grouped = df_esports_grouped[df_esports_grouped['Instal·lacions'] > 0]

    # Tipus: Treemap
    # Representem la jerarquia i el pes proporcional de l'equimant esportiu en cada comarca
    fig_g4 = px.treemap(
        df_esports_grouped,
        path=['Comarca', 'Esport'],
        values='Instal·lacions',
        title="Distribució proporcional dels esports segons la comarca (La mida del bloc representa el total d'instal·lacions)",
        color='Instal·lacions',
        color_continuous_scale='Viridis',
        height=800
    )
    st.plotly_chart(fig_g4, width='stretch')

# ------------------------------------------------------------------------------
# Pestanya 4: L'impacte econòmic
# ------------------------------------------------------------------------------
with tab4:
    st.header("Estadística: Creuant riquesa i equipaments")

    st.subheader("Gràfic 5: Correlació comarcal")
    df_comarca_eco = df.groupby(["Comarca", "Titularitat"]).agg(
        PIB_Mitja=("valor", "mean"),
        Total_Centres=("Ref INS", "count")
    ).reset_index()

    # Tipus: Gràfic de dispersió (Scatter plot) amb línia de tendència
    # Nosaltres utilitzem aquest gràfic per observar si existeix una relació lineal entre la riquesa econòmica (PIB) i el nombre d'equipaments esportius.
    fig_g5 = px.scatter(
        df_comarca_eco, x="PIB_Mitja", y="Total_Centres", color="Titularitat",
        size="Total_Centres", hover_name="Comarca", trendline="ols",
        title="PIB comarcal mitjà vs total d'infraestructures",
        labels={"PIB_Mitja": "PIB Mitjà per habitant de la comarca (€)", "Total_Centres": "Equipaments totals"},
        height=800
    )
    st.plotly_chart(fig_g5, width='stretch')

# Peu de pàgina
st.markdown("---")
st.markdown("*Projecte de Visualització de Dades, UOC. Integració de dades macroeconòmiques de l'IDESCAT (2021) i el Cens d'Equipaments Esportius de Catalunya  (2024). Nora Bolivar*")
