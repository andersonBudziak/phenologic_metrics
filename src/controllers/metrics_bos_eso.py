import pandas as pd

class BosEosMetrics:
    """
    A class for analyzing NDVI (Normalized Difference Vegetation Index) data.
    """

    def __init__(self, df_index: pd.DataFrame, phenology_df: pd.DataFrame, threshold: float ):
        """
        Initialize the NDVIAnalysis class with a pandas DataFrame.

        :param ndvi_df: DataFrame containing NDVI and other related data.
        """
        self.df_index = df_index
        self.phenology_df = phenology_df
        self.threshold = threshold

    def find_phenologic_dates(self):
        """
        Find the dates for 'vos_start', 'pos', and 'vos_end' in the DataFrame.
        """
        self.vos_start_date = self.phenology_df.loc[self.phenology_df['Phenologic'] == 'vos_start', 'Date'].values[0]
        self.pos_date = self.phenology_df.loc[self.phenology_df['Phenologic'] == 'pos', 'Date'].values[0]
        self.vos_end_date = self.phenology_df.loc[self.phenology_df['Phenologic'] == 'vos_end', 'Date'].values[0]

    def filter_interval(self):
        """
        Filter the DataFrame for the interval between 'vos_start' and 'vos_end'.
        """
        self.interval_df = self.df_index.loc[(self.df_index['timestamps'] >= self.vos_start_date) & 
                                            (self.df_index['timestamps'] <= self.vos_end_date)]

    def calculate_first_derivative(self):
        """
        Calculate the first derivative of the NDVI in the interval.
        """
        self.interval_df['first_derivative'] = self.interval_df['savitzky_golay'].diff().fillna(0)

    def identify_bos_eos_der(self):
        """
        Identify the Beginning of Season (BOS) and End of Season (EOS) in the phenological interval.
        """
        self.BOS_date = self.interval_df['first_derivative'].idxmax()  # First peak after 'vos_start'
        self.EOS_date = self.interval_df.loc[self.interval_df['timestamps'] >= self.pos_date]['first_derivative'].idxmin()  # First drop after 'pos'

        bos_der_start_row = pd.DataFrame({
            'Date': [self.df_index.loc[self.BOS_date, 'timestamps']],
            'Value': [self.df_index.loc[self.BOS_date, 'savitzky_golay']],
            'Phenologic': ['bos_der']
        })

        eos_der_start_row = pd.DataFrame({
            'Date': [self.df_index.loc[self.EOS_date, 'timestamps']],
            'Value': [self.df_index.loc[self.EOS_date, 'savitzky_golay']],
            'Phenologic': ['eos_der']
        })

        # Concatenate rows into a new DataFrame
        self.phenology_df = pd.concat([self.phenology_df, bos_der_start_row, eos_der_start_row], ignore_index=True)

        return self.phenology_df


    def identify_bos_eos_abs(self):
        """
        Identify the Beginning of Season (BOS) and End of Season (EOS) in the phenological interval.
        """
        # Find the two closest values to the threshold
        self.closest_indexes = (self.interval_df['savitzky_golay'] - self.threshold).abs().nsmallest(2).index

        bos_der_start_row = pd.DataFrame({
            'Date': [self.df_index.loc[self.closest_indexes[1], 'timestamps']],
            'Value': [self.df_index.loc[self.closest_indexes[1], 'savitzky_golay']],
            'Phenologic': ['bos_abs']
        })

        eos_der_start_row = pd.DataFrame({
            'Date': [self.df_index.loc[self.closest_indexes[0], 'timestamps']],
            'Value': [self.df_index.loc[self.closest_indexes[0], 'savitzky_golay']],
            'Phenologic': ['eos_abs']
        })

        # Concatenate rows into a new DataFrame
        self.phenology_df = pd.concat([self.phenology_df, bos_der_start_row, eos_der_start_row], ignore_index=True)

    def execute_analysis(self):
        """
        Execute the complete NDVI analysis workflow.
        """
        self.find_phenologic_dates()
        self.filter_interval()
        self.calculate_first_derivative()
        self.identify_bos_eos_der()
        self.identify_bos_eos_abs()

        return self.phenology_df
