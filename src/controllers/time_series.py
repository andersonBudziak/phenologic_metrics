import pandas as pd
from scipy.signal import savgol_filter

class VegetationIndexProcessor:
    def __init__(self, df, vegetation_index, window_size, poly_order):
        self.df = df
        self.vegetation_index = vegetation_index
        self.window_size = window_size
        self.poly_order = poly_order

    def process(self):
        if len(self.df) < 15:
            print('Not enough images!')
            return self.df

        # Smooth time series the index
        self.df['savitzky_golay'] = savgol_filter(
            self.df[self.vegetation_index], 
            self.window_size, 
            self.poly_order
        )

        # Converting the 'date_image' column to datetime format
        self.df['timestamps'] = pd.to_datetime(self.df['date_image'])

        # Resampling dates to daily frequency
        self.df.set_index('timestamps', inplace=True)
        self.df = self.df.resample('D').interpolate(method='linear')

        # Set datestamp and reset index
        self.df['timestamps'] = self.df.index
        self.df.reset_index(drop=True, inplace=True)
        
        return self.df