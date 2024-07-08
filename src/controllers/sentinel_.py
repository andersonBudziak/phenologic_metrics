import ee
import pandas as pd

class Sentinel2Processor:
    def __init__(self, start_date, end_date, geometry, cloud_threshold=30):
        """
        Initialize the Sentinel2Processor class.

        Parameters:
        start_date (str): The start date for the image collection filter.
        end_date (str): The end date for the image collection filter.
        geometry (ee.Geometry): The geometry to filter the image collection.
        cloud_threshold (int): The cloud probability threshold for masking clouds.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.geometry = geometry
        self.cloud_threshold = cloud_threshold

    def mask_clouds_and_shadows(self, image):
        """
        Mask clouds and shadows in the image.

        Parameters:
        image (ee.Image): The image to mask.

        Returns:
        ee.Image: The masked image.
        """
        cloud_prob = image.select('MSK_CLDPRB')
        snow_prob = image.select('MSK_SNWPRB')
        clouds = cloud_prob.lt(self.cloud_threshold)
        snow = snow_prob.lt(self.cloud_threshold)
        scl = image.select('SCL')
        mask_conditions = (
            clouds.And(snow)
            .And(scl.neq(1))
            .And(scl.neq(2))
            .And(scl.neq(3))
            .And(scl.neq(6))
            .And(scl.neq(7))
            .And(scl.neq(8))
            .And(scl.neq(9))
            .And(scl.neq(10))
            .And(scl.neq(11))
        )
        return image.updateMask(mask_conditions)

    def add_ndvi(self, image):
        """
        Add NDVI band to the image.

        Parameters:
        image (ee.Image): The image to add NDVI.

        Returns:
        ee.Image: The image with the NDVI band.
        """
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)

    def add_evi(self, image):
        """
        Add EVI band to the image.

        Parameters:
        image (ee.Image): The image to add EVI.

        Returns:
        ee.Image: The image with the EVI band.
        """
        evi = image.expression(
            '2.5 * ((B8 - B4) / (B8 + 6 * B6 - 7.5 * B2) + 1)',
            {
                'B8': image.select('B8'),
                'B6': image.select('B6'),
                'B4': image.select('B4'),
                'B2': image.select('B2')
            }
        ).rename('EVI')
        return image.addBands(evi)

    def extract_indexes(self, image):
        """
        Extract NDVI and EVI indexes from the image.

        Parameters:
        image (ee.Image): The image to extract indexes from.

        Returns:
        ee.Feature: The feature containing NDVI, EVI, and date.
        """
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=self.geometry,
            scale=10,
            maxPixels=1e10
        )

        ndvi = ee.List([stats.get('NDVI'), -9999]).reduce(ee.Reducer.firstNonNull())
        evi = ee.List([stats.get('EVI'), -9999]).reduce(ee.Reducer.firstNonNull())

        feature = ee.Feature(
            None,
            {
                'ndvi': ndvi,
                'evi': evi,
                'date': ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')
            }
        )
        return feature
    
    def remove_rows_with_last_string(self, df, column_name, string_to_keep):
        """
        Remove rows where the last string in the specified column is not equal to the given string.
        
        Parameters:
        df (pd.DataFrame): The input DataFrame.
        column_name (str): The name of the column to check.
        string_to_keep (str): The string to keep at the end of the column's values.
        
        Returns:
        pd.DataFrame: The DataFrame with the specified rows kept.
        """
        # Split the column by underscores and check the last part
        mask = df[column_name].str[-1] == string_to_keep
        return df[mask]

    def filter_and_process_image_collection(self):
        """
        Filter and process the Sentinel-2 image collection.

        Returns:
        ee.ImageCollection: The processed image collection.
        """
        collection = (
            ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterDate(self.start_date, self.end_date)
            .filterBounds(self.geometry)
            .map(self.mask_clouds_and_shadows)
            .map(self.add_ndvi)
            .map(self.add_evi)
        )
        return collection

    def map_and_extract_indexes(self, collection):
        """
        Map over the collection and extract indexes.

        Parameters:
        collection (ee.ImageCollection): The image collection to process.

        Returns:
        dict: A dictionary containing the time series data.
        """
        time_series = collection.map(self.extract_indexes)
        time_series_dict = time_series.getInfo()
        return time_series_dict

    def transform_to_dataframe(self, time_series_dict):
        """
        Transform the time series dictionary to a pandas DataFrame.

        Parameters:
        time_series_dict (dict): The time series dictionary.

        Returns:
        pd.DataFrame: The DataFrame containing the time series data.
        """
        data = []
        for feature in time_series_dict['features']:
            properties = feature['properties']
            data.append([
                feature['id'],
                properties['date'],
                properties['ndvi'],
                properties['evi']
            ])
        df = pd.DataFrame(data, columns=['id_image', 'date_image', 'ndvi_value', 'evi_value'])
        return df

    def clean_and_filter_dataframe(self, df):
        """
        Clean and filter the DataFrame by removing invalid values.

        Parameters:
        df (pd.DataFrame): The input DataFrame.

        Returns:
        pd.DataFrame: The cleaned and filtered DataFrame.
        """
        df_filtered = df.copy()
        df_filtered[['ndvi_value', 'evi_value']] = df_filtered[['ndvi_value', 'evi_value']].applymap(
            lambda x: None if x < 0 else x)
        df_filtered[['ndvi_value', 'evi_value']] = df_filtered[['ndvi_value', 'evi_value']].replace(-9999, None)
        df_filtered.dropna(subset=['ndvi_value', 'evi_value'], inplace=True)
        return df_filtered

    def filter_rows_by_condition(self, df_filtered):
        """
        Filter rows by a specific condition.

        Parameters:
        df_filtered (pd.DataFrame): The DataFrame to filter.

        Returns:
        pd.DataFrame: The filtered DataFrame.
        """
        df_filtered = self.remove_rows_with_last_string(df_filtered, 'id_image', 'V').reset_index(drop=True)
        return df_filtered

    def process_data(self):
        """
        Process the data by filtering and extracting indexes.

        Returns:
        pd.DataFrame: The processed DataFrame.
        """
        collection = self.filter_and_process_image_collection()
        time_series_dict = self.map_and_extract_indexes(collection)
        df = self.transform_to_dataframe(time_series_dict)
        df_filtered = self.clean_and_filter_dataframe(df)
        df_filtered = self.filter_rows_by_condition(df_filtered)
        return df_filtered
    

    def get_filtered_df(self):
        """
        Get the filtered DataFrame.

        Returns:
        pd.DataFrame: The filtered DataFrame.
        """
        collection = (
            ee.ImageCollection('COPERNICUS/S2_SR')
            .filterDate(self.start_date, self.end_date)
            .filterBounds(self.geometry)
            .map(self.mask_clouds_and_shadows)
            .map(self.add_ndvi)
            .map(self.add_evi)
        )

        time_series = collection.map(self.extract_indexes)
        time_series_dict = time_series.getInfo()

        data = []
        for feature in time_series_dict['features']:
            properties = feature['properties']
            data.append([
                feature['id'],
                properties['date'],
                properties['ndvi'],
                properties['evi']
            ])

        df = pd.DataFrame(data, columns=['id_image', 'date_image', 'ndvi_value', 'evi_value'])
        df_filtered = df.copy()

        df_filtered[['ndvi_value', 'evi_value']] = df_filtered[['ndvi_value', 'evi_value']].applymap(
            lambda x: None if x < 0 else x)
        df_filtered[['ndvi_value', 'evi_value']] = df_filtered[['ndvi_value', 'evi_value']].replace(-9999, None)
        df_filtered.dropna(subset=['ndvi_value', 'evi_value'], inplace=True)

        df_filtered = self.remove_rows_with_last_string(df_filtered, 'id_image', 'V').reset_index()

        return df_filtered
