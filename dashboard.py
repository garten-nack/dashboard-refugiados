import streamlit as st
import pandas as pd 
import plotly as pl 
import requests
import zipfile
import os
import altair as alt
import vega_datasets
import plotly.graph_objects as go


#################################################################
# Funcoes
#################################################################

def debugger(objeto):
    if _DEBUG_:
        st.write(objeto)


def downloadDadosZip(file_url):
    arquivo = "temp"

    # Fazer o download do arquivo
    response = requests.get(file_url)
    with open(arquivo, 'wb') as file:
        file.write(response.content)

    # Descompactar o arquivo ZIP
    with zipfile.ZipFile(arquivo, 'rb') as zip_ref:
        zip_ref.extractall("./dados/")

    # Remover o arquivo ZIP após a extração
    os.remove(arquivo)

def formataNumero(valor, prefixo = '', decimais = 2):
    for unidade in ['','mil']:
        if valor < 1000:
            return f'{prefixo} {valor:.{decimais}f} {unidade}'
        valor /= 1000

    return f'{prefixo} {valor:.{decimais}f} milhões'


@st.cache_data
def lerDados():
    downloadDadosZip("https://drive.google.com/uc?export=download&id=1S203NPfSJobD224bRnqlQhyD5WgkVrz5")
    df = pd.read_csv("dados/dados-processados.csv", sep=";")
    return df

@st.cache_data
def lerMapaMundi():
    return alt.topo_feature(vega_datasets.data.world_110m.url, 'countries')

@st.cache_data
def listaTipoPopulacao(df):
    return df['TipoPopulacao'].unique()

@st.cache_data
def listaRegiaoUNHCR(df):
    return df['RegiaoUNHCROrigem'].unique()

@st.cache_data
def listaRegiaoUNSD(df):
    return df['RegiaoUNSDOrigem'].unique()

@st.cache_data
def listaSubRegiaoUNSD(df):
    return df['SubRegiaoUNSDOrigem'].unique()

@st.cache_data
def listaRegiaoSGD(df):
    return df['RegiaoSGDOrigem'].unique()

@st.cache_data
def listaPais(df):
    return df['PaisOrigem'].unique()

@st.cache_data
def listaIntervaloAno(df):
    return df['Ano'].min(), df['Ano'].max()

@st.cache_data
def listaPaisesOrigem(df):
    return df['NomePaisOrigem'].unique()

@st.cache_data
def listaPaisesAsilo(df):
    return df['NomePaisAsilo'].unique()


def formataTP(opcao):
    if opcao == 'ASY':
        return 'Em busca de asilo'
    elif opcao == 'OIP':
        return 'Proteção internacional'
    elif opcao == 'REF':
        return 'Refugiados'
    elif opcao == 'ROC':
        return 'Análogo a refugiados'
    else:
        return 'Desconhecido'
    
def filtroAnoTipoPopulacao(df, filtroAnos, filtroTP):
    filtro = (df['Ano'] >= filtroAnos[0]) & (df['Ano'] <= filtroAnos[1]) & (df['TipoPopulacao'].isin(filtroTP))
    return df[filtro]


############################
# filtros para o sidebar
############################
    
def addFiltroAnos(df):
    todosAnos = st.sidebar.toggle("Dados de todo o período", value = True)
    anoMin, anoMax = listaIntervaloAno(df)
    if todosAnos:
        selecao = (anoMin, anoMax)
    else:
        selecao = st.sidebar.slider('**Ano**', anoMin, anoMax, value = (anoMin, anoMax))
    debugger(f'Intervalo anos: {selecao}')
    return selecao

def addFiltroFluxo():
    st.sidebar.divider()
    selecao = st.sidebar.radio('**Sumarizar por**',['Origem','Asilo'])
    debugger(f'Sumarizar por: {selecao}')
    return selecao


def addFiltroTipoPopulacao(df):
    st.sidebar.divider()
    lista = listaTipoPopulacao(df)
    selecao = st.sidebar.multiselect('**Tipo de população**',
                                    lista, 
                                    default=lista,                                  
                                    format_func=formataTP,
                                    placeholder='Selecione as opções...')
    debugger(f'MTPSelected: {selecao}')    
    return selecao


############
# Graficos
############

def refugiadosPorTipo(df):
    descriptions = {
        'ASY': 'ASY - Em busca de asilo',
        'OIP': 'OIP - Proteção internacional',
        'REF': 'REF - Refugiados',
        'ROC': 'ROC - Análogo a refugiados'
    }

    df_summed = df.groupby('TipoPopulacao')['Quantidade'].sum().reset_index()
    df_summed['Descricao'] = df_summed['TipoPopulacao'].map(descriptions)


    # Criando o gráfico de barras em Altair
    chart = alt.Chart(df_summed).mark_bar().encode(
        x=alt.X('TipoPopulacao:N', title='Tipo'),
        y=alt.Y('Quantidade:Q', scale=alt.Scale(type='linear', base=10), title='Quantidade'),
        color=alt.Color('Descricao:N', legend=alt.Legend(title="Tipo")),
        tooltip=['TipoPopulacao', 'Quantidade']
    ).properties(
        width=710,
        height=400,
        title='Quantidade de refugiados por tipo'
    )
    st.altair_chart(chart, use_container_width=False)

def refugiadosPorAno(df):
    df_acum_ano = df.groupby('Ano')['Quantidade'].sum().reset_index()
    chart = alt.Chart(df_acum_ano).mark_bar().encode(
        x=alt.X('Ano:O', bin=alt.Bin(maxbins=40), title='Anos'),
        y=alt.Y('Quantidade:Q', scale=alt.Scale(type='linear', base=10), title='Quantidade de refugiados'),
        color=alt.Color('Ano:O', scale=alt.Scale(scheme='category20'), legend=None),
        tooltip=['Ano', 'Quantidade']
    ).properties(
        width=1020,
        height=600,
        title='Quantidade de refugiados por ano'
    )
    st.altair_chart(chart, use_container_width=False)

def refugiadosPorRegiao(df, regiao, tit_x='Região', tit_chart='Refugiados por região'):
    df_summed = df.groupby(regiao)['Quantidade'].sum().reset_index()
    chart = alt.Chart(df_summed).mark_bar().encode(
        x=alt.X(f'{regiao}:O', title=tit_x),
        y=alt.Y('Quantidade:Q', scale=alt.Scale(type='linear', base=10), title='Número de refugiados'),
        color=alt.Color(f'{regiao}:N', legend=alt.Legend(title="Regiões")),
        tooltip=[regiao, 'Quantidade']
    ).properties(
        width=1020,
        height=600,
        title=tit_chart
    )
    st.altair_chart(chart, use_container_width=False)

def refugiadosPorAnoRegiao(df, regiao, tit_chart='Refugiados por ano e região'):
    df_regiao = df.groupby(['Ano', regiao])['Quantidade'].sum().reset_index()

    chart = alt.Chart(df_regiao).mark_bar().encode(
        x=alt.X('Ano:O', title='Ano'),
        y=alt.Y('Quantidade:Q', title='Quantidade de refugiados'),
        color=alt.Color(f'{regiao}:N', title='Regiões'),
        tooltip=['Ano', regiao, 'Quantidade']
    ).properties(
        width=1280,
        height=700,
        title=tit_chart
    )
    st.altair_chart(chart, use_container_width=False)

# sentido: Origem | Destino
def topNRefugiados(df, topn, sentido, tit_chart):
    pais = 'NomePais' + sentido
    top_paises = df.groupby(pais)['Quantidade'].sum().reset_index().sort_values('Quantidade', ascending=False).head(topn)

    # Criando o gráfico de barras em Altair
    chart = alt.Chart(top_paises).mark_bar().encode(
        x=alt.X(f'{pais}:N', sort='-y', title='País'),
        y=alt.Y('Quantidade:Q', title='Quantidade'),
        color=alt.Color(f'{pais}:N', title='País'),
        tooltip=[alt.Tooltip(f'{pais}:N', title='País'), alt.Tooltip('Quantidade:Q', title='Quantidade')]

    ).properties(
        width=710,
        height=400,
        title=tit_chart
    )
    st.altair_chart(chart, use_container_width=False)


# sentido: Origem | Destino
def refugiadosMapaMundi(df, countries, sentido, tit_chart):   
    pais = 'NomePais' + sentido
    latitude = 'Latitude' + sentido
    longitude = 'Longitude' + sentido
    df_paises = df.groupby(pais).agg({'Quantidade': 'sum', latitude: 'min', longitude: 'min'}).reset_index()

    chart = alt.Chart(df_paises).mark_circle(stroke="black").encode(
        longitude=f'{longitude}:Q',
        latitude=f'{latitude}:Q',
        size=alt.Size('Quantidade:Q', scale=alt.Scale(type='linear'), title='Quantidade'),
        color=alt.Color(f'{pais}:N', legend=None),
        tooltip=[f'{pais}:N', 'Quantidade:Q']
    ).properties(
        width=1280,
        height=700,
        title=tit_chart
    )    

    # Adicionar o mapa de fundo dos países
    background = alt.Chart(countries).mark_geoshape(
        fill='lightgray',
        stroke='white'
    ).properties(
        width=1280,
        height=700
    )

    st.altair_chart((background + chart).project(scale=200), use_container_width=True)



# sentido: Origem | Destino
def agruparOutrosPaises(df, origem, asilo, topn = None):

    # Ordenar o DataFrame por 'Quantidade' em ordem decrescente
    aggregated_df = df.groupby(['NomePaisOrigem', 'NomePaisAsilo']).agg({'Quantidade': 'sum'}).reset_index().sort_values(by='Quantidade', ascending=False)

    if topn == None:
        return aggregated_df
    else:
        # Separar os topn registros
        top_df = aggregated_df.head(topn)

        # Agregar os demais registros
        others_df = aggregated_df.iloc[topn:]

        # Se há registros em others_df, agregue-os
        if not others_df.empty:
            nomePaisGrupo = 'NomePais' + origem
            nomePaisOutros = 'NomePais' + asilo
            others_aggregated = others_df.groupby([nomePaisGrupo]).agg({'Quantidade': 'sum'}).reset_index()
            others_aggregated[nomePaisOutros] = 'Outros'
            # Concatenar os topn registros com os agregados 'Outros'
            final_df = pd.concat([top_df, others_aggregated]).sort_values(by='Quantidade', ascending=False)
        else:
            final_df = top_df

        return final_df


def refugiadosPorPais(df):

    # Criando listas de labels únicas para os nós
    all_countries = pd.concat([df['NomePaisOrigem'], df['NomePaisAsilo']]).unique()

    # Mapeando países a índices
    country_idx = {country: idx for idx, country in enumerate(all_countries)}

    # Criando os dados de origem, destino e quantidades para o gráfico de Sankey
    source = [country_idx[src] for src in df['NomePaisOrigem']]
    target = [country_idx[dst] for dst in df['NomePaisAsilo']]
    values = df['Quantidade'].tolist()

    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=30,
            thickness=20,
            line=dict(color="black", width=1.0),
            label=list(all_countries)
        ),
        link=dict(
            arrowlen=30,
            source=source,  # Índices dos países de origem
            target=target,  # Índices dos países destino
            value=values,  # Quantidade de movimentação
            color='#EEEEEE' #F2EFE5'#F5EFE6' #F2EFE5'#'#EFEFEF'#'#F1F1F1'#'#EADBC8'
        ))])

    # Configurando o layout
    fig.update_layout(title_text="Fluxo de Movimentação entre Países", 
                      font=dict(size = 20),
                      height=768)

    
    st.plotly_chart(fig, use_container_width=True)


def agruparOutrosPaisesTipoPopulacao(df, origem, asilo, topn = None):

    # Ordenar o DataFrame por 'Quantidade' em ordem decrescente
    aggregated_df = df.groupby(['NomePaisOrigem', 'TipoPopulacao', 'NomePaisAsilo']).agg({'Quantidade': 'sum'}).reset_index().sort_values(by='Quantidade', ascending=False)

    if topn == None:
        return aggregated_df
    else:
        # Separar os topn registros
        top_df = aggregated_df.head(topn)

        # Agregar os demais registros
        others_df = aggregated_df.iloc[topn:]

        # Se há registros em others_df, agregue-os
        if not others_df.empty:
            nomePaisGrupo = 'NomePais' + origem
            nomePaisOutros = 'NomePais' + asilo
            others_aggregated = others_df.groupby([nomePaisGrupo,'TipoPopulacao']).agg({'Quantidade': 'sum'}).reset_index()
            others_aggregated[nomePaisOutros] = 'Outros'
            # Concatenar os topn registros com os agregados 'Outros'
            final_df = pd.concat([top_df, others_aggregated]).sort_values(by='Quantidade', ascending=False)
        else:
            final_df = top_df

        return final_df


def refugiadosPorPaisTipoPopulacao(df):
    unique_nodes = pd.concat([df['NomePaisOrigem'], df['TipoPopulacao'], df['NomePaisAsilo']]).unique()
    node_dict = {node: i for i, node in enumerate(unique_nodes)}

    source = []
    target = []
    values = []

    for _, row in df.iterrows():
        source.append(node_dict[row['NomePaisOrigem']])
        target.append(node_dict[row['TipoPopulacao']])
        values.append(row['Quantidade'])

        source.append(node_dict[row['TipoPopulacao']])
        target.append(node_dict[row['NomePaisAsilo']])
        values.append(row['Quantidade'])   

    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=30,
            thickness=20,
            line=dict(color="black", width=1.0),
            label=list(unique_nodes)
        ),
        link=dict(
            arrowlen=30,
            source=source,  # Índices dos países de origem
            target=target,  # Índices dos países destino
            value=values,  # Quantidade de movimentação
            color='#EEEEEE'
        ))])

    # Configurando o layout
    fig.update_layout(title_text='Fluxo de Movimentação entre Países de origem e asilo', 
                      font=dict(size = 20),
                      height=768)

    
    st.plotly_chart(fig, use_container_width=True)




#################################################################
# Principal
#################################################################

# habilitar visualização de variáveis na tela
_DEBUG_ = False

# configuracoes do streamlit
st.set_page_config(layout='wide', 
                   page_title='Dashboard - Refugiados',
                   page_icon=':earth_africa:')

#configuracoes do altair
alt.data_transformers.disable_max_rows()

# https://streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app/
st.title("REFUGIADOS NO MUNDO :earth_africa:")

df = lerDados()

countries = lerMapaMundi()

st.sidebar.title('Filtros')

filtroAnos = addFiltroAnos(df)
filtroFluxo = addFiltroFluxo()
filtroTP = addFiltroTipoPopulacao(df)

df_filtrado = filtroAnoTipoPopulacao(df, filtroAnos, filtroTP)

abaGeral, abaUNHCR, abaUNSD, abaSubUNSD, abaMapa, abaOrigemAsilo = st.tabs(['Geral','Regiões das Nações Unidas','Continentes','Sub Regiões','Mapa Mundi', 'Fluxo Origem/Asilo'])

with abaGeral:
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total de refugiados", formataNumero(df_filtrado['Quantidade'].sum()))    
        refugiadosPorTipo(df_filtrado)
    with c2:        
        tituloGeral = 'Países de ' + filtroFluxo
        campoGeral = 'SiglaPais' + filtroFluxo
        st.metric(tituloGeral, formataNumero(df_filtrado[campoGeral].nunique(), decimais=0))
        topNRefugiados(df_filtrado, 10, filtroFluxo, 'Top 10 países de ' + filtroFluxo.lower() + ' de refugiados')

    
    refugiadosPorAno(df_filtrado)
    st.dataframe(df_filtrado)
    

with abaUNHCR:
    with st.expander('**Filtro de Regiões**'):
        filtroUNHCR = st.multiselect('Regiões',
                            listaRegiaoUNHCR(df_filtrado), 
                            default=listaRegiaoUNHCR(df_filtrado),                                  
                            placeholder='Selecione as opções...')

    if filtroFluxo == 'Origem':
        df_filtrado_origem = df_filtrado[df_filtrado['RegiaoUNHCROrigem'].isin(filtroUNHCR)]
        refugiadosPorRegiao(df_filtrado_origem, 'RegiaoUNHCROrigem', 'Região de origem', 'Refugiados por região de origem')
        refugiadosPorAnoRegiao(df_filtrado_origem, 'RegiaoUNHCROrigem', 'Refugiados por ano e região de origem')
    else:
        df_filtrado_asilo  = df_filtrado[df_filtrado['RegiaoUNHCRAsilo'].isin(filtroUNHCR)]
        refugiadosPorRegiao(df_filtrado_asilo, 'RegiaoUNHCRAsilo', 'Região de asilo', 'Refugiados por região de asilo')
        refugiadosPorAnoRegiao(df_filtrado_asilo, 'RegiaoUNHCRAsilo', 'Refugiados por ano e região de asilo')

with abaUNSD:
    with st.expander('**Filtro de Continentes**'):
        filtroUNSD = st.multiselect('Continentes',
                            listaRegiaoUNSD(df_filtrado), 
                            default=listaRegiaoUNSD(df_filtrado),                                  
                            placeholder='Selecione as opções...')

    if filtroFluxo == 'Origem':
        df_filtrado_origem = df_filtrado[df_filtrado['RegiaoUNSDOrigem'].isin(filtroUNSD)]
        refugiadosPorRegiao(df_filtrado_origem, 'RegiaoUNSDOrigem', 'Continente de origem', 'Refugiados por continente de origem')
        refugiadosPorAnoRegiao(df_filtrado_origem, 'RegiaoUNSDOrigem', 'Refugiados por ano e continente de origem')
    else:
        df_filtrado_asilo = df_filtrado[df_filtrado['RegiaoUNSDAsilo'].isin(filtroUNSD)]
        refugiadosPorRegiao(df_filtrado_asilo, 'RegiaoUNSDAsilo', 'Continente de asilo', 'Refugiados por continente de asilo')
        refugiadosPorAnoRegiao(df_filtrado_asilo, 'RegiaoUNSDAsilo', 'Refugiados por ano e continente de asilo')

with abaSubUNSD:
    with st.expander('**Filtro de Sub-regiões**'):
        filtroSubRegioes = st.multiselect('Sub-regiões',
                            listaSubRegiaoUNSD(df_filtrado), 
                            default=listaSubRegiaoUNSD(df_filtrado),                                  
                            placeholder='Selecione as opções...')
        
    if filtroFluxo == 'Origem':        
        df_filtrado_origem = df_filtrado[df_filtrado['SubRegiaoUNSDOrigem'].isin(filtroSubRegioes)]
        refugiadosPorRegiao(df_filtrado_origem, 'SubRegiaoUNSDOrigem', 'Sub-região de origem', 'Refugiados por sub-região de origem')
        refugiadosPorAnoRegiao(df_filtrado_origem, 'SubRegiaoUNSDOrigem', 'Refugiados por ano e sub-região de origem')
    else:
        df_filtrado_asilo = df_filtrado[df_filtrado['SubRegiaoUNSDAsilo'].isin(filtroSubRegioes)]
        refugiadosPorRegiao(df_filtrado_asilo, 'SubRegiaoUNSDAsilo', 'Sub-região de asilo', 'Refugiados por sub-região de asilo')
        refugiadosPorAnoRegiao(df_filtrado_asilo, 'SubRegiaoUNSDAsilo', 'Refugiados por ano e sub-região de asilo')

with abaMapa:
    if filtroFluxo == 'Origem':
        #refugiadosMapaMundi(df_filtrado, countries, 'Origem', 'Países de origem de refugiados')
        refugiadosMapaMundi(df_filtrado, countries, 'Origem', 'Países de origem de refugiados')
    else:
        refugiadosMapaMundi(df_filtrado, countries, 'Asilo', 'Países que concederam asilo para refugiados')

with abaOrigemAsilo:

    if filtroFluxo == 'Origem':
        with st.expander('**Filtro de país de origem**'):
            filtroPaisOrigem = st.selectbox('País',
                                listaPaisesOrigem(df_filtrado),
                                index=None,
                                placeholder='Selecione uma opção...')
            
            df_filtrado_origem = df_filtrado.loc[df_filtrado['NomePaisOrigem'] == filtroPaisOrigem, ['NomePaisOrigem', 'TipoPopulacao', 'NomePaisAsilo', 'Quantidade']]        

            todosAsilos = False
            if todosAsilos:
                topAsilo = None
            else:
                topAsilo = st.number_input("Mostrar no máximo", min_value=1, max_value=10, value=10, step=1, key="idAsilo")

            df_filtrado_origem_top_asilo = agruparOutrosPaisesTipoPopulacao(df_filtrado_origem, 'Origem', 'Asilo', topAsilo)        
            refugiadosPorPaisTipoPopulacao(df_filtrado_origem_top_asilo)
    else:
        with st.expander('**Filtro de país de asilo**'):
            filtroPaisAsilo = st.selectbox('País',
                                listaPaisesAsilo(df_filtrado),
                                index=None,
                                placeholder='Selecione uma opção...')
            
            df_filtrado_asilo = df_filtrado.loc[df_filtrado['NomePaisAsilo'] == filtroPaisAsilo, ['NomePaisOrigem', 'TipoPopulacao', 'NomePaisAsilo', 'Quantidade']]
            
            todosOrigens = False
            if todosOrigens:
                topOrigem = None
            else:
                topOrigem = st.number_input("Mostrar no máximo", min_value=1, max_value=10, value=10, step=1, key="idOrigem")
            
            df_filtrado_asilo_top_origem = agruparOutrosPaisesTipoPopulacao(df_filtrado_asilo, 'Asilo', 'Origem', topOrigem)        
            refugiadosPorPaisTipoPopulacao(df_filtrado_asilo_top_origem)

