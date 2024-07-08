import ee

from src.controllers.plotter_base import PhenologyPlotter
from src.controllers.metrics_vos_pos import VosPosMetrics
from src.controllers.metrics_bos_eso import BosEosMetrics
from src.controllers.sentinel_ import  Sentinel2Processor
from src.controllers.geometry import ProcessadorGeoDataFrame
from src.controllers.metrics_geometrics import PhenologyMetrics
from src.controllers.time_series import VegetationIndexProcessor
from src.controllers.eras import PrecipitationTemperatureRadiationData

# Trigger the authentication flow.
ee.Authenticate()

# Initialize the library.
ee.Initialize(project='ee-carbonei')


if __name__ == "__main__":
    # Datas de análise
    start_date = '2023-01-01'
    end_date = '2023-12-30'

    #Paht polygons
    path = r'data\ms_field_boundaries.gpkg'

    #Index polygon, defoult is 0
    index_poligon = 3

    cloud_probality = 0.5

    vegetation_index = 'ndvi_value'

    trheasould_index = 2.8


    # Aplicar o filtro Savitzky-Golay
    window_size = 30
    poly_order = 4

    #Order NDVI
    order = 20

        #Read geometry file
    processador = ProcessadorGeoDataFrame(path)
    vertices, geometry = processador.extrair_coordenadas(index_poligon)

    # Convert points to a polygon
    polygon = ee.Geometry.Polygon(vertices)

    s2 = Sentinel2Processor(start_date, end_date, polygon)
    df = s2.process_data()

    processor = VegetationIndexProcessor(df, vegetation_index, window_size=7, poly_order=2)
    df = processor.process()

    #Get and VOS and POS metrics
    vos_pos_analyzer = VosPosMetrics(df, order)
    phenology_df = vos_pos_analyzer.analyze_phenology()

    #Get and BOS and EOS metrics
    analysis = BosEosMetrics(df, phenology_df, trheasould_index)
    phenology_df = analysis.execute_analysis()

    analysis_metrics = PhenologyMetrics(phenology_df, df)
    phenology_df = analysis_metrics.derivate_metrics()

    plotter = PhenologyPlotter(df, phenology_df, vegetation_index)
    fig = plotter.plot_data()

    fig.show()

    fig_1 = plotter.plot_data_01()

    fig_1.show()

    # Usage
    lat = geometry.getInfo()['coordinates'][0][0][1]  # Exemplo de latitude
    lon = geometry.getInfo()['coordinates'][0][0][0]  # Exemplo de longitude

    data = PrecipitationTemperatureRadiationData(lat, lon, start_date, end_date)
    df = data.get_dataframe()
    fig_precipitation = data.plot_precipitation()
    fig_temperature = data.plot_temperature()
    fig_radiation = data.plot_radiation()

    # Show the DataFrame
    print(df)

    # Show the interactive plots
    fig_precipitation.show()
    fig_temperature.show()
    fig_radiation.show()