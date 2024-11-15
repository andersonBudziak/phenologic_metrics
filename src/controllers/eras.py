import ee
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

class PrecipitationTemperatureRadiationData:
    def __init__(self, lat, lon, start_date, end_date):
        self.lat = lat
        self.lon = lon
        self.start_date = start_date
        self.end_date = end_date
        self.point = ee.Geometry.Point(lon, lat)
        self.df = None

    def _fetch_data(self):
        ppt = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")\
            .select("total_precipitation_sum")\
            .filterBounds(self.point)\
            .filterDate(self.start_date, self.end_date)

        temp = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")\
            .select("temperature_2m_max")\
            .filterBounds(self.point)\
            .filterDate(self.start_date, self.end_date)
        
        radiation = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")\
            .select("surface_net_solar_radiation_sum")\
            .filterBounds(self.point)\
            .filterDate(self.start_date, self.end_date)

        def add_date_temp_radiation(image):
            date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')
            mean_ppt = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=self.point,
                scale=5566
            ).get('total_precipitation_sum')
            
            corresponding_temp = temp.filterDate(
                image.date().format('YYYY-MM-dd')
            ).first().reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=self.point,
                scale=5566
            ).get('temperature_2m_max')
            
            corresponding_radiation = radiation.filterDate(
                image.date().format('YYYY-MM-dd')
            ).first().reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=self.point,
                scale=5566
            ).get('surface_net_solar_radiation_sum')
            
            return ee.Feature(None, {
                'date': date,
                'sum_precipitation': mean_ppt,
                'temperature_2m_max': corresponding_temp,
                'surface_net_solar_radiation_sum': corresponding_radiation
            })

        data_collection = ppt.map(add_date_temp_radiation)
        data = data_collection.getInfo()
        features = data['features']
        data_list = [{'date': f['properties']['date'],
                      'mean_precipitation': f['properties']['sum_precipitation'] * 1000,
                      'temperature_2m_max': f['properties']['temperature_2m_max'],
                      'surface_net_solar_radiation_sum': f['properties']['surface_net_solar_radiation_sum']} for f in features]
        self.df  = pd.DataFrame(data_list)
        return self.df

    def get_dataframe(self):
        df = self._fetch_data()
        df['date'] = pd.to_datetime(df['date'])
        df['temperature_2m_max'] = df['temperature_2m_max'].apply(lambda x: x - 273.15)  # Convert from Kelvin to Celsius
        self.df = df
        return self.df

    def plot_precipitation(self):

        df = self.df

        # Gráfico de barras para a precipitação diária
        fig = px.bar(df, x='date', y='mean_precipitation', title='Sum Daily Precipitation',
                    labels={'date': 'Date', 'mean_precipitation': 'Sum Precipitation (mm)'}, 
                    color_discrete_sequence=['#642834'])

        non_zero_df = df[df['cumulative_precipitation'] != 0]

        # Adicionar o gráfico de linha para a precipitação acumulada usando um segundo eixo Y
        fig.add_trace(
            go.Scatter(x=non_zero_df['date'], y=non_zero_df['cumulative_precipitation'], mode='lines', name='Cumulative Precipitation', 
                    line=dict(color='#304D30'), yaxis='y2')
        )

        # Atualizar o layout para adicionar um segundo eixo Y
        fig.update_layout(
            yaxis=dict(
                title='Sum Precipitation (mm)',
                titlefont=dict(color='black'),
                tickfont=dict(color='black')
            ),
            yaxis2=dict(
                title='Cumulative Precipitation (mm)',
                titlefont=dict(color='black'),
                tickfont=dict(color='black'),
                overlaying='y',
                side='right'
            ),
            legend=dict(
                x=0.01,
                y=0.99
            )
        )

        return fig

    def plot_temperature(self):
        df = self.df
        fig = px.bar(df, x='date', y='temperature_2m_max', title='Max Daily Temperature',
                      labels={'date': 'Date', 'temperature_2m_max': 'Max Temperature (°C)'}, 
                      color_discrete_sequence=['#642834'])
        return fig
    
    def plot_radiation(self):
        df = self.df
        fig = px.bar(df, x='date', y='surface_net_solar_radiation_sum', title='Surface Net Thermal Radiation',
                      labels={'date': 'Date', 'surface_net_solar_radiation_sum': 'Surface Net Thermal Radiation (J/m²)'}, 
                      color_discrete_sequence=['#642834'])
        return fig
    
    def preciptation_sum(self, phenology_df):

        df = self.df

        # Filtrar as datas de início e término
        vos_start_dates = phenology_df[phenology_df['Phenologic'] == 'vos_start']['Date']
        vos_end_dates = phenology_df[phenology_df['Phenologic'] == 'vos_end']['Date']

        # Garantir que temos o mesmo número de datas de início e término
        assert len(vos_start_dates) == len(vos_end_dates), "Número diferente de datas 'vos_start' e 'vos_end'"

        # Inicializar uma nova coluna com zeros para o acumulado de precipitação
        df['cumulative_precipitation'] = 0

        # Para cada par de datas de início e término, calcular o acumulado diário de precipitação
        for start_date, end_date in zip(vos_start_dates, vos_end_dates):
            mask = (df['date'] >= start_date) & (df['date'] <= end_date)
            df.loc[mask, 'cumulative_precipitation'] = df.loc[mask, 'mean_precipitation'].cumsum()

        return df