import pandas as pd

class PhenologyMetrics:
    def __init__(self, phenology_df, ndvi_df ):
        self.phenology_df = phenology_df
        self.ndvi_df = ndvi_df

    def days_between(self, start_event, end_event):
        """Calculate the number of days between two phenological events."""
        start_date = self.phenology_df.loc[self.phenology_df['Phenologic'] == start_event, 'Date'].values[0]
        end_date = self.phenology_df.loc[self.phenology_df['Phenologic'] == end_event, 'Date'].values[0]
        return (end_date - start_date ).astype('timedelta64[D]').astype(int)

    def vertical_difference(self, start_event, end_event):
        """Calculate the vertical difference (in NDVI value) between two events."""
        start_value = self.phenology_df.loc[self.phenology_df['Phenologic'] == start_event, 'Value'].values[0]
        end_value = self.phenology_df.loc[self.phenology_df['Phenologic'] == end_event, 'Value'].values[0]
        return end_value - start_value

    def horizontal_difference(self, start_event, end_event):
        """Calculate the horizontal difference (in days) between two events."""
        return self.days_between(start_event, end_event)
    
    def percentil_difference(self):
        start_date = self.phenology_df.loc[self.phenology_df['Phenologic'] == 'bos_abs', 'Date'].values[0]
        end_date = self.phenology_df.loc[self.phenology_df['Phenologic'] == 'eos_abs', 'Date'].values[0]

        # Filtrar as linhas entre as datas especificadas
        mask = (self.ndvi_df['timestamps'] >=  end_date) & (self.ndvi_df['timestamps'] <= start_date)
        filtered_data = self.ndvi_df.loc[mask]

        # Calcular o valor do percentil na coluna NDVI
        percentile_value = filtered_data['savitzky_golay'].quantile(85 / 100)

        # Contar quantos valores de NDVI estão acima do valor do percentil
        return (filtered_data['savitzky_golay'] > percentile_value).sum()
    
    def derivate_metrics(self):
        # Assuming phenology_metrics is an instance of a class with these methods
        df_metrics = pd.DataFrame([
            {'Value': self.days_between('vos_start', 'vos_end'),
            'Phenologic': 'Days between vos_end and vos_start'},#1

            {'Value': self.days_between(   'eos_abs', 'bos_abs'),
            'Phenologic': 'Days between bos_abs and eos_abs'},#2

            {'Value': self.vertical_difference('bos_abs', 'pos'),
            'Phenologic': 'NDVI difference between bos_abs and pos'},#3

            {'Value': self.horizontal_difference( 'pos', 'bos_abs'),
            'Phenologic': 'Days difference between bos_abs and pos'},#4

            {'Value': self.horizontal_difference('vos_start', 'bos_abs'),
            'Phenologic': 'Days difference between vos_start and bos_abs'},#5

            {'Value': self.vertical_difference('vos_start', 'bos_abs'),
            'Phenologic': 'NDVI difference between vos_start and bos_abs'},#6

            {'Value': self.horizontal_difference('eos_abs', 'vos_end'),
            'Phenologic': 'Days difference between vos_end and eos_abs'},#7

            {'Value': self.vertical_difference(  'eos_abs', 'pos'),
            'Phenologic': 'NDVI difference between eos_abs and pos'},#8

            {'Value': self.horizontal_difference( 'eos_abs', 'pos'),
            'Phenologic': 'Days difference between eos_abs and pos'},#9

            {'Value': self.vertical_difference('vos_end', 'eos_abs'),
            'Phenologic': 'NDVI difference between eos_abs and vos_end'},#10

            {'Value': self.percentil_difference(),
            'Phenologic': 'Count 85% percentiles days between bos_abs and eos_abs'}
        ])

        # Concatenate rows into a new DataFrame
        self.phenology_df = pd.concat([self.phenology_df, df_metrics], ignore_index=True)

        return self.phenology_df

