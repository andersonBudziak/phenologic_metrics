import ee
import pandas as pd

class Landsat:
    def __init__(self, polygon, start_date, end_date):
        self.polygon = ee.Geometry.Polygon(polygon)
        self.start_date = start_date
        self.end_date = end_date

    @staticmethod
    def maskL8L9(image):
        cloudShadowBitMask = 1 << 3
        cloudsBitMask = 1 << 5
        qa = image.select('QA_PIXEL')
        mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0).And(
            qa.bitwiseAnd(cloudsBitMask).eq(0)
        )
        return image.updateMask(mask)

    @staticmethod
    def addIndicesLandsat(image):
        ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
        evi = image.expression(
            '2.5 * (((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE)) + 1)',
            {
                'NIR': image.select('SR_B5'),
                'RED': image.select('SR_B4'),
                'BLUE': image.select('SR_B2')
            }
        ).rename('EVI')
        return image.addBands([ndvi, evi])

    def extract_values(self):
        landsat8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
            .filterBounds(self.polygon) \
            .filterDate(self.start_date, self.end_date) \
            .map(self.maskL8L9) \
            .map(self.addIndicesLandsat) \
            .map(lambda image: image.set('SATELLITE', 'Landsat8'))

        landsat9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2') \
            .filterBounds(self.polygon) \
            .filterDate(self.start_date, self.end_date) \
            .map(self.maskL8L9) \
            .map(self.addIndicesLandsat) \
            .map(lambda image: image.set('SATELLITE', 'Landsat9'))

        merged = landsat8.merge(landsat9)

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
                'SATELLITE': image.get('SATELLITE'),
                'image_id': image_id
            })

        values = merged.map(extract).getInfo()
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
