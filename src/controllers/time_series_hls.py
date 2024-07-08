import ee
import pandas as pd

class HLS:

    def __init__(self, geometry, start_date, end_date):
        """
        Initializes Landsat class with specified geometry, start date, and end date.
        
        Args:
            geometry (ee.Geometry): Geometry for the image collection.
            start_date (str): Start date in "YYYY-MM-DD" format.
            end_date (str): End date in "YYYY-MM-DD" format.
        """
        self.geometry = geometry
        self.start_date = start_date
        self.end_date = end_date

    def add_ndvi_band(self, image):
        """
        Adds NDVI (Normalized Difference Vegetation Index) band to a Landsat image.
        
        Args:
            image (ee.Image): Landsat image.
        
        Returns:
            ee.Image: Landsat image with NDVI band added.
        """
        nir = image.select('B5')
        red = image.select('B4')
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        return image.addBands(ndvi)

    def calculate_statistics_for_region(self, image):
        """
        Calculates region statistics for a given image.
        
        Args:
            image (ee.Image): The input image.
        
        Returns:
            ee.Feature: Feature containing region statistics as properties.
        """
        statistics = image.reduceRegion(reducer=ee.Reducer.median(),
                                        geometry=self.geometry,
                                        scale=10)
        feature = ee.Feature(None, statistics)
        return feature

    def extract_fmask_bitwise(self, image):
        """
        Extracts Fmask for cloud and cloud shadow conditions.
        
        Args:
            image (ee.Image): Landsat image.
        
        Returns:
            ee.Image: Masked Landsat image.
        """
        clouds_bit_mask = 1 << 1
        cloud_shadow_bit_mask = 1 << 3
        qa = image.select('Fmask')
        mask = qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0) \
               .And(qa.bitwiseAnd(clouds_bit_mask).eq(0))
        return image.updateMask(mask)

    def add_ndvi_with_fmask(self, image):
        """
        Adds NDVI band and copies properties from original image.
        
        Args:
            image (ee.Image): Landsat image.
        
        Returns:
            ee.Image: Image with NDVI band.
        """
        nir = image.select('B5')
        red = image.select('B4')
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        return ndvi.copyProperties(image, ['system:time_start'])

    def create_image_collection(self):
        """
        Creates an image collection for the specified time period and geometry.
        
        Returns:
            ee.ImageCollection: Collection of processed images.
        """
        collection = ee.ImageCollection("NASA/HLS/HLSL30/v002")\
                        .filterBounds(self.geometry)\
                        .filter(ee.Filter.date(self.start_date, self.end_date))\
                        .map(self.extract_fmask_bitwise)\
                        .map(self.add_ndvi_band)\
                        .map(self.calculate_statistics_for_region)
        return collection

    def convert_to_dataframe(self):
            """
            Converts the image collection to a pandas DataFrame with NDVI values, dates, and IDs.

            Returns:
                pandas.DataFrame: A DataFrame with columns for date, ID, NDVI values, and satellite name.
            """
            collection_info = self.create_image_collection().getInfo()['features']
            
            # Extracting data from each image in the collection
            data = [{
                'date': image['id'].split('_')[1][:8],
                'id': image['id'],
                'ndvi': image['properties']['NDVI']
            } for image in collection_info]

            # Creating DataFrame and processing
            df = pd.DataFrame(data)
            df['satellite'] = 'landsat'
            df.dropna(inplace=True)

            # Handling date and sorting
            df['date'] = pd.to_datetime(df['date'])
            df.sort_values('date', inplace=True)
            df = df.drop_duplicates(subset='date').reset_index(drop=True)

            # Resampling dates to daily frequency
            df.set_index('date', inplace=True)
            df = df.resample('D').interpolate(method='linear')

            #Set datestamp and reset index
            df.reset_index(inplace=True)

            # Convertendo a coluna 'date' para o formato datetime
            df['timestamps'] = pd.to_datetime(df['date'])

            return df
