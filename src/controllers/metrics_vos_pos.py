import numpy as np
import pandas as pd
from scipy import signal

class VosPosMetrics:
    """
    A class for analyzing NDVI data to identify key phenological stages.
    
    Attributes:
        ndvi_df (pd.DataFrame): DataFrame containing NDVI data.
        order_ndvi (int): Order parameter for finding extrema in NDVI data.
    """

    def __init__(self, df_index, order):
        """
        Inicializa o NDVIAnalyzer com o DataFrame e a ordem do NDVI.

        Args:
            ndvi_df (pd.DataFrame): DataFrame contendo os dados NDVI.
            order_ndvi (int): Ordem para encontrar extremos nos dados NDVI.
        """
        self.df_index = df_index
        self.order = order

    def find_peaks(self):
        """
        Encontra os picos (máximos) nos dados NDVI.

        Returns:
            np.ndarray: Índices dos picos encontrados nos dados NDVI.
        """
        return signal.argrelextrema(self.df_index['savitzky_golay'].to_numpy(), 
                                    np.greater, order=self.order)[0]

    def find_valleys(self):
        """
        Encontra os vales (mínimos) nos dados NDVI.

        Returns:
            np.ndarray: Índices dos vales encontrados nos dados NDVI.
        """
        return signal.argrelextrema(self.df_index['savitzky_golay'].to_numpy(), 
                                    np.less, order=self.order)[0]

    def analyze_phenology(self):
        """
        Analyzes phenology, identifying phenological stages and marking them in a new DataFrame.

        Returns:
            pd.DataFrame: A new DataFrame with phenological markings.
        """
        peak_indexes = self.find_peaks()
        max_peak_index = np.argmax(self.df_index['savitzky_golay'].iloc[peak_indexes])
        
        valley_indexes = self.find_valleys()
        before_valley_index = max(valley_indexes[valley_indexes < peak_indexes[max_peak_index]])
        after_valley_index = min(valley_indexes[valley_indexes > peak_indexes[max_peak_index]])

        # Create rows for the new DataFrame
        vos_start_row = pd.DataFrame({
            'Date': [self.df_index.loc[before_valley_index, 'timestamps']],
            'Value': [self.df_index.loc[before_valley_index, 'savitzky_golay']],
            'Phenologic': ['vos_start']
        })

        vos_end_row = pd.DataFrame({
            'Date': [self.df_index.loc[after_valley_index, 'timestamps']],
            'Value': [self.df_index.loc[after_valley_index, 'savitzky_golay']],
            'Phenologic': ['vos_end']
        })

        pos_row = pd.DataFrame({
            'Date': [self.df_index.loc[peak_indexes[max_peak_index], 'timestamps']],
            'Value': [self.df_index.loc[peak_indexes[max_peak_index], 'savitzky_golay']],
            'Phenologic': ['pos']
        })

        # Concatenate rows into a new DataFrame
        phenology_df = pd.concat([vos_start_row, vos_end_row, pos_row], ignore_index=True)

        return phenology_df


