import ee
import pandas as pd

class Sentinel2:
    def __init__(self, polygon, start_date, end_date):
        self.polygon = ee.Geometry.Polygon(polygon)
        self.start_date = start_date
        self.end_date = end_date

    @staticmethod
    def add_ndvi(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)

    @staticmethod
    def add_evi(image):
        evi = image.expression(
            '2.5 * (((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE)) + 1)',
            {
                'NIR': image.select('B8'),
                'RED': image.select('B4'),
                'BLUE': image.select('B2')
            }
        ).rename('EVI')
        return image.addBands(evi)

    @staticmethod
    def mask_clouds(image):
        qa = image.select('QA60')
        cloud_bit_mask = ee.Number(2).pow(10).int()
        cirrus_bit_mask = ee.Number(2).pow(11).int()
        mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
            qa.bitwiseAnd(cirrus_bit_mask).eq(0))
        return image.updateMask(mask)

    def extract_values(self):
        collection = ee.ImageCollection('COPERNICUS/S2_SR') \
            .filterDate(self.start_date, self.end_date) \
            .filterBounds(self.polygon) \
            .map(self.mask_clouds) \
            .map(self.add_ndvi) \
            .map(self.add_evi)

        def extract(image):
            stats = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=self.polygon,
                scale=30,
                maxPixels=1e9
            )
            ndvi = stats.get('NDVI')
            evi = stats.get('EVI')
            time = image.get('system:time_start')
            image_id = image.get('system:index')
            return ee.Feature(None, {
                'time': ee.Date(time).format('YYYY-MM-dd'),
                'NDVI': ndvi,
                'EVI': evi,
                'SATELLITE': 'Sentinel-2',
                'image_id': image_id
            })

        values = collection.map(extract).getInfo()
        features = values['features']
        data = [{
            'time': f['properties']['time'],
            'NDVI': f['properties']['NDVI'],
            'EVI': f['properties']['EVI'],
            'SATELLITE': f['properties']['SATELLITE'],
            'image_id': f['properties']['image_id']
        } for f in features]
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'])
        return df
