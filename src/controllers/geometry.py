import ee  # Asumindo que você está usando a biblioteca Earth Engine
import geopandas as gpd


class ProcessadorGeoDataFrame:
    def __init__(self, arquivo):
        self.gdf = self.ler_arquivo(arquivo)

    def ler_arquivo(self, arquivo):
        # Carregar o arquivo em um GeoDataFrame e ajustar o CRS
        gdf = gpd.read_file(arquivo)
        gdf = gdf.explode(ignore_index=True)
        gdf = gdf.to_crs("epsg:4326")
        return gdf

    def extrair_coordenadas(self, index_poligono : int):
        # Extrair os vértices do polígono especificado
        polygon = self.gdf.geometry.iloc[index_poligono]
        vertices = list(polygon.exterior.coords)
        
        # Formatando os vértices
        vertices_formatados = [[coord[0], coord[1]] for coord in vertices]

        # Define a geometria para uso no Earth Engine, se necessário
        geometry = ee.Geometry.Polygon([vertices_formatados])

        return vertices_formatados, geometry


