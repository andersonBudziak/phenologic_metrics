import ee
import pandas as pd
import plotly.express as px

class PrecipitationTemperatureRadiationData:
    def __init__(self, lat, lon, start_date, end_date):
        self.lat = lat
        self.lon = lon
        self.start_date = start_date
        self.end_date = end_date
        self.point = ee.Geometry.Point(lon, lat)

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
        return pd.DataFrame(data_list)

    def get_dataframe(self):
        df = self._fetch_data()
        df['date'] = pd.to_datetime(df['date'])
        df['temperature_2m_max'] = df['temperature_2m_max'].apply(lambda x: x - 273.15)  # Convert from Kelvin to Celsius
        return df

    def plot_precipitation(self):
        df = self.get_dataframe()
        fig = px.bar(df, x='date', y='mean_precipitation', title='Sum Daily Precipitation',
                      labels={'date': 'Date', 'mean_precipitation': 'Sum Precipitation (mm)'}, 
                      color_discrete_sequence=['#642834'])
        return fig

    def plot_temperature(self):
        df = self.get_dataframe()
        fig = px.bar(df, x='date', y='temperature_2m_max', title='Max Daily Temperature',
                      labels={'date': 'Date', 'temperature_2m_max': 'Max Temperature (°C)'}, 
                      color_discrete_sequence=['#642834'])
        return fig
    
    def plot_radiation(self):
        df = self.get_dataframe()
        fig = px.bar(df, x='date', y='surface_net_solar_radiation_sum', title='Surface Net Thermal Radiation',
                      labels={'date': 'Date', 'surface_net_solar_radiation_sum': 'Surface Net Thermal Radiation (J/m²)'}, 
                      color_discrete_sequence=['#642834'])
        return fig